"""IA: conversaciones con dueño, clave del tenant por request y rol en la configuración.

Cubre: un segundo usuario con el `conversation_id` del primero → 404 sin `Message`
nuevo; `conversation_id` malformado → 400; con clave propia del tenant, la clave no
queda en `os.environ` y llega a `litellm.completion` como `api_key`; viewer PUT
config → 403 y admin PUT → 200; `calcular_prestamo` rechaza plazos fuera de 1..600.
"""

import os
from types import SimpleNamespace
from unittest import mock

import pytest
from django.db import connection
from django.test import override_settings
from djangosdk.models.conversation import Conversation
from djangosdk.models.message import Message
from rest_framework.test import APIClient

from apps.ai.tools import calcular_prestamo
from apps.tenants.models import Tenant

TENANT_HOST = "tenant.test.localhost"
CHAT_URL = "/api/ai/chat/"
CONFIG_URL = "/api/ai/config/"
TENANT_KEY = "tenant-secret-key-9f3c"


def _fake_completion(**kwargs):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Hola", tool_calls=None))],
        model=kwargs.get("model", ""),
        usage=None,
    )


@pytest.fixture
def completion_mock():
    with mock.patch("litellm.completion", side_effect=_fake_completion) as patched:
        yield patched


@pytest.fixture
def ai_enabled(tenant_schema):
    with override_settings(AI_ENABLED=True):
        yield


@pytest.fixture
def tenant_key(tenant_schema):
    Tenant.objects.filter(pk=tenant_schema.pk).update(
        enable_ai_assistant=True,
        ai_provider="groq",
        ai_model="groq/llama-test",
        ai_api_key=TENANT_KEY,
    )
    return TENANT_KEY


def _client(user):
    client = APIClient(HTTP_HOST=TENANT_HOST)
    client.force_authenticate(user=user)
    return client


def _chat(client, **data):
    data.setdefault("prompt", "Hola")
    data.setdefault("agent", "lite")
    return client.post(CHAT_URL, data, format="json")


def test_other_users_conversation_is_not_found(user_factory, ai_enabled, tenant_key, completion_mock):
    owner = _client(user_factory(role="loan_officer"))
    first = _chat(owner)
    assert first.status_code == 200, first.data
    conversation_id = first.data["conversation_id"]
    assert conversation_id
    messages_before = Message.objects.filter(conversation_id=conversation_id).count()
    calls_before = completion_mock.call_count

    intruder = _client(user_factory(role="loan_officer"))
    response = _chat(intruder, conversation_id=conversation_id)

    assert response.status_code == 404
    assert response.data == {"error": "Conversación no encontrada."}
    assert Message.objects.filter(conversation_id=conversation_id).count() == messages_before
    assert completion_mock.call_count == calls_before


def test_owner_can_continue_own_conversation(user_factory, ai_enabled, tenant_key, completion_mock):
    user = user_factory(role="loan_officer")
    client = _client(user)
    first = _chat(client)
    conversation_id = first.data["conversation_id"]
    conversation = Conversation.objects.get(id=conversation_id)
    assert conversation.metadata == {"user_id": user.pk, "schema": connection.schema_name}

    second = _chat(client, conversation_id=conversation_id)

    assert second.status_code == 200, second.data
    assert str(second.data["conversation_id"]) == str(conversation_id)
    assert Message.objects.filter(conversation_id=conversation_id).count() == 4


def test_malformed_conversation_id_is_400(user_factory, ai_enabled, tenant_key, completion_mock):
    client = _client(user_factory(role="loan_officer"))

    response = _chat(client, conversation_id="no-es-un-uuid")

    assert response.status_code == 400
    assert response.data == {"error": "conversation_id inválido."}
    completion_mock.assert_not_called()


def test_tenant_key_is_passed_per_request_not_via_environ(
    user_factory, ai_enabled, tenant_key, completion_mock
):
    client = _client(user_factory(role="loan_officer"))

    response = _chat(client)

    assert response.status_code == 200, response.data
    assert TENANT_KEY not in os.environ.values()
    completion_mock.assert_called_once()
    assert completion_mock.call_args.kwargs["api_key"] == TENANT_KEY
    assert completion_mock.call_args.kwargs["model"] == "groq/llama-test"


@pytest.mark.parametrize(
    "model, expected_model",
    [("", "openai/gpt-4o-mini"), ("gpt-4o-mini", "openai/gpt-4o-mini"), ("gpt-4.1", "openai/gpt-4.1")],
)
def test_tenant_key_only_goes_to_tenant_provider(
    user_factory, ai_enabled, tenant_schema, completion_mock, model, expected_model
):
    """La clave OpenAI del tenant nunca se enruta al proveedor global (groq)."""
    Tenant.objects.filter(pk=tenant_schema.pk).update(
        enable_ai_assistant=True, ai_provider="openai", ai_model=model, ai_api_key=TENANT_KEY
    )
    client = _client(user_factory(role="loan_officer"))

    response = _chat(client)

    assert response.status_code == 200, response.data
    completion_mock.assert_called_once()
    assert completion_mock.call_args.kwargs["model"] == expected_model
    assert completion_mock.call_args.kwargs["api_key"] == TENANT_KEY


def test_viewer_cannot_put_ai_config(user_factory, tenant_schema):
    client = _client(user_factory(role="viewer", is_staff=True))

    response = client.put(CONFIG_URL, {"api_key": "robada", "provider": "openai"}, format="json")

    assert response.status_code == 403
    assert response.data == {"error": "Solo administradores pueden cambiar la configuración AI."}
    tenant = Tenant.objects.get(pk=tenant_schema.pk)
    assert tenant.ai_api_key != "robada"
    assert tenant.ai_provider != "openai"


def test_admin_can_put_ai_config(user_factory, tenant_schema):
    client = _client(user_factory(role="admin"))

    response = client.put(CONFIG_URL, {"provider": "openai", "model": "gpt-test"}, format="json")

    assert response.status_code == 200, response.data
    tenant = Tenant.objects.get(pk=tenant_schema.pk)
    assert tenant.ai_provider == "openai"
    assert tenant.ai_model == "gpt-test"


@pytest.mark.parametrize("plazo", [0, -1, 601, 10**6])
def test_calcular_prestamo_rejects_out_of_range_term(plazo):
    result = calcular_prestamo(monto=10000, tasa_mensual=3, plazo_meses=plazo)

    assert result == "plazo_meses debe estar entre 1 y 600."


def test_calcular_prestamo_accepts_valid_term():
    result = calcular_prestamo(monto=10000, tasa_mensual=3, plazo_meses=12)

    assert "Plazo: 12 meses" in result
