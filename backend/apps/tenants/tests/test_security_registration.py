"""Registro público de tenants: throttle propio, tope diario, nombres reservados y errores uniformes."""
import pytest
from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from rest_framework.settings import api_settings

from apps.tenants.models import Domain, Tenant
from apps.users.models import User

pytestmark = pytest.mark.django_db

URL = "/api/tenants/register/"
GENERIC = "No se pudo completar el registro con estos datos."


def payload(**overrides):
    data = {
        "business_name": "Financiera Nueva SRL",
        "tenant_name": "financiera-nueva",
        "email": "contacto@nueva.test",
        "subdomain": "financiera-nueva",
        "owner_first_name": "Ana",
        "owner_last_name": "Gomez",
        "owner_email": "ana@nueva.test",
        "owner_password": "Kx9!vRt#2mQw7zLp",
        "subscription_plan": "basic",
    }
    data.update(overrides)
    return data


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


def counts():
    return Tenant.objects.count(), User.objects.count(), Domain.objects.count()


def throttled_settings():
    rf = dict(api_settings.user_settings)
    rf["DEFAULT_THROTTLE_RATES"] = {"tenant_registration": "3/hour"}
    return override_settings(REST_FRAMEWORK=rf)


def test_fourth_registration_from_same_ip_in_an_hour_is_throttled(public_client):
    # Peticiones inválidas a propósito: el throttle cuenta intentos, no altas.
    bad = payload(owner_email="no-es-un-correo")
    with throttled_settings():
        for _ in range(3):
            assert public_client.post(URL, bad, format="json").status_code == 400
        before = counts()
        response = public_client.post(URL, payload(), format="json")
    assert response.status_code == 429
    assert counts() == before


def test_authenticated_tenant_user_is_throttled_too(auth_client):
    # /api/tenants/register/ también está montado en los hosts de tenant: un usuario
    # autenticado no puede saltarse el throttle (ni agotar MAX_TENANTS_PER_DAY).
    bad = payload(owner_email="no-es-un-correo")
    with throttled_settings():
        for _ in range(3):
            assert auth_client.post(URL, bad, format="json").status_code == 400
        before = counts()
        response = auth_client.post(URL, payload(), format="json")
    assert response.status_code == 429
    assert counts() == before


def test_registration_throttle_keys_on_client_ip_behind_proxy(public_client):
    bad = payload(owner_email="no-es-un-correo")
    rf = dict(api_settings.user_settings)
    rf["DEFAULT_THROTTLE_RATES"] = {"tenant_registration": "3/hour"}
    rf["NUM_PROXIES"] = 1
    with override_settings(REST_FRAMEWORK=rf):
        for i in range(3):
            response = public_client.post(
                URL, bad, format="json", REMOTE_ADDR="172.18.0.5", HTTP_X_FORWARDED_FOR=f"203.0.113.{i}"
            )
            assert response.status_code == 400
        # Otro cliente detrás del mismo proxy conserva su cupo.
        response = public_client.post(
            URL, bad, format="json", REMOTE_ADDR="172.18.0.5", HTTP_X_FORWARDED_FOR="198.51.100.7"
        )
        assert response.status_code == 400


@pytest.mark.parametrize("name", ["public", "test", "pg-catalog", "pg-foo", "information-schema", "www"])
def test_reserved_or_existing_schema_names_are_rejected(public_client, tenant, name):
    before = counts()
    response = public_client.post(URL, payload(tenant_name=name), format="json")
    assert response.status_code == 400
    assert response.json() == {"non_field_errors": [GENERIC]}
    assert counts() == before


@pytest.mark.parametrize(
    "name", ["contracts", "billing", "tenants", "avatars", "customer-documents", "media", "static"]
)
def test_legacy_media_folder_names_are_reserved(public_client, name):
    # Un schema con el nombre de una carpeta antigua de media saltaría el chequeo
    # schema/archivo de SignedMediaView (_name_matches_schema).
    before = counts()
    response = public_client.post(URL, payload(tenant_name=name, subdomain=f"{name}-x"), format="json")
    assert response.status_code == 400
    assert response.json() == {"non_field_errors": [GENERIC]}
    assert counts() == before


TENANT_NAME_FORMAT = (
    "El nombre del tenant debe empezar con una letra minúscula y contener sólo letras "
    "minúsculas, números y guiones (máximo 63 caracteres)."
)


@pytest.mark.parametrize("name", ["1abc", "a" * 64, "-abc", "abc_def", "abc def", ""])
def test_tenant_name_format_errors_are_specific(public_client, name):
    before = counts()
    response = public_client.post(URL, payload(tenant_name=name), format="json")
    assert response.status_code == 400
    if name:  # vacío: lo rechaza antes el CharField ("This field may not be blank.")
        assert response.json() == {"tenant_name": [TENANT_NAME_FORMAT]}
    assert counts() == before


@pytest.mark.parametrize("raw, normalized", [("abc-1", "abc-1"), ("  Abc-1 ", "abc-1"), ("a" * 63, "a" * 63)])
def test_tenant_name_format_accepts_valid_names(raw, normalized):
    from apps.tenants.serializers import TenantRegistrationSerializer

    serializer = TenantRegistrationSerializer(data=payload(tenant_name=raw))
    serializer.is_valid()
    assert "tenant_name" not in serializer.errors
    assert serializer.validate_tenant_name(raw) == normalized


def test_every_legacy_media_dir_is_a_reserved_schema():
    from apps.core.media import LEGACY_TOP_DIRS
    from apps.tenants.serializers import _RESERVED_SCHEMAS

    assert LEGACY_TOP_DIRS <= _RESERVED_SCHEMAS
    assert {"media", "static", "public"} <= _RESERVED_SCHEMAS


def test_name_whose_schema_exists_only_in_postgres_is_rejected(public_client):
    with connection.cursor() as cursor:
        cursor.execute("CREATE SCHEMA huerfano_schema")
    before = counts()
    response = public_client.post(URL, payload(tenant_name="huerfano-schema"), format="json")
    assert response.status_code == 400
    assert response.json() == {"non_field_errors": [GENERIC]}
    assert counts() == before


def test_existence_of_email_name_or_subdomain_is_indistinguishable(public_client, tenant, user_factory):
    user_factory(email="ocupado@nueva.test")
    connection.set_schema_to_public()
    Tenant.objects.filter(pk=tenant.pk).update(name="ocupado")
    # El subdominio se compara con el dominio exacto que crearía el registro (run-5): el del
    # tenant de pruebas, `tenant.test.localhost`, ya no choca con `tenant` por contenerlo.
    Domain.objects.create(domain="sub-ocupado", tenant=tenant, is_primary=False)
    before = counts()
    by_email = public_client.post(URL, payload(owner_email="ocupado@nueva.test"), format="json")
    by_name = public_client.post(URL, payload(tenant_name="ocupado"), format="json")
    by_subdomain = public_client.post(URL, payload(subdomain="sub-ocupado"), format="json")
    for response in (by_email, by_name, by_subdomain):
        assert response.status_code == 400
    assert by_email.json() == by_name.json() == by_subdomain.json() == {"non_field_errors": [GENERIC]}
    assert counts() == before


def test_format_errors_keep_their_specific_messages(public_client):
    response = public_client.post(URL, payload(owner_email="no-es-un-correo", tenant_name="1mayus"), format="json")
    assert response.status_code == 400
    body = response.json()
    assert "owner_email" in body and "tenant_name" in body
    assert GENERIC not in str(body)


@override_settings(MAX_TENANTS_PER_DAY=0, MAX_PENDING_REGISTRATIONS_HARD_CEILING=0)
def test_daily_caps_reject_new_registrations(public_client):
    # Por encima del tope global el registro queda pendiente (202); sólo con el techo de
    # pendientes también agotado se rechaza (MAX_PENDING_REGISTRATIONS_PER_DAY ya sólo
    # avisa; ver test_security_registration_network).
    before = counts()
    response = public_client.post(URL, payload(), format="json")
    assert response.status_code == 400
    assert GENERIC in str(response.json())
    assert counts() == before


def test_internal_error_returns_generic_400_without_details(public_client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("detalle interno secreto")

    monkeypatch.setattr(Domain.objects, "create", boom)
    monkeypatch.setattr(Tenant, "auto_create_schema", False)
    before = counts()
    response = public_client.post(URL, payload(), format="json")
    assert response.status_code == 400
    assert response.json() == {"detail": GENERIC}
    assert "secreto" not in response.content.decode()
    assert counts() == before


def test_valid_registration_creates_tenant(public_client):
    before_tenants = Tenant.objects.count()
    response = public_client.post(URL, payload(), format="json")
    assert response.status_code == 201, response.content
    assert Tenant.objects.count() == before_tenants + 1
    tenant = Tenant.objects.get(name="financiera-nueva")
    assert tenant.schema_name == "financiera_nueva"
    assert User.objects.filter(email="ana@nueva.test", tenant=tenant, is_tenant_owner=True).exists()
