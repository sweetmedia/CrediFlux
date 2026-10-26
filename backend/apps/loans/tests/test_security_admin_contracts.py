"""El admin de contratos y de enlaces de firma sigue las reglas de la API (ronda 25).

`ContractAdmin` sólo dependía de los permisos de modelo: un staff con rol viewer o cashier (al que
la API responde 403) revivía un contrato cancelado, fijaba `customer_signed_at` sin firma,
reescribía el texto de un contrato firmado y lo borraba, uno a uno o con la acción masiva
(run-5, ContractAdmin-no-lifecycle-guards-status-content-signatures-delete). Ahora exige el rol de
`CanManageLoans`, sólo deja editar `special_terms`, `notes`, `witness_name` y `witness_id`, guarda
sobre la fila bloqueada rechazando los estados terminales y sólo borra lo que borra
`ContractViewSet.perform_destroy` (mismo predicado).

`ContractSignatureTokenAdmin` dejaba extender un enlace vencido, activar la firma como oficial y
mostraba el token, con el que se firmaba por el endpoint público
(run-5, ContractSignatureTokenAdmin-editable-expiry-sign-scope-visible-token). Ahora es de sólo
lectura para todos y nunca muestra ni busca el token.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"
TOKEN = "r25-token-de-prueba-0123456789abcdef"
CONTRACT_PERMS = ["view_contract", "add_contract", "change_contract", "delete_contract"]
TOKEN_PERMS = [
    "view_contractsignaturetoken", "add_contractsignaturetoken",
    "change_contractsignaturetoken", "delete_contractsignaturetoken",
]


def _staff(user_factory, role, codenames):
    from apps.users.models import User

    user = user_factory(role=role, is_staff=True)
    user.user_permissions.add(*Permission.objects.filter(content_type__app_label="loans", codename__in=codenames))
    return User.objects.get(pk=user.pk)  # sin la caché de permisos


def _client(user):
    client = Client(HTTP_HOST=HOST)
    client.force_login(user)
    return client


@pytest.fixture
def manager_client(user_factory):
    return _client(_staff(user_factory, "manager", CONTRACT_PERMS))


@pytest.fixture
def template():
    from apps.loans.models_contracts import ContractTemplate

    return ContractTemplate.objects.create(name="Base r25", content="Préstamo {{loan_number}}", is_active=True)


def _pending_loan(loan_factory):
    return loan_factory(status="pending", disbursement_date=None, interest_rate=Decimal("1.50"))


def _contract(loan, template, **extra):
    from apps.loans.models_contracts import Contract

    data = {"content": "texto firmado", "status": "pending_signature", "notes": "nota vieja"}
    data.update(extra)
    return Contract.objects.create(loan=loan, template=template, **data)


def _change_body(contract, **overrides):
    """Formulario completo como lo enviaría un POST manipulado: incluye estado, texto y firmas."""
    now = timezone.localtime()
    body = {
        "loan": str(contract.loan_id), "template": str(contract.template_id),
        "status": "signed", "content": "TEXTO REESCRITO",
        "customer_signed_at_0": now.strftime("%Y-%m-%d"), "customer_signed_at_1": now.strftime("%H:%M:%S"),
        "officer_signed_at_0": now.strftime("%Y-%m-%d"), "officer_signed_at_1": now.strftime("%H:%M:%S"),
        "witness_signed_at_0": "", "witness_signed_at_1": "",
        "special_terms": "", "notes": "nota nueva", "witness_name": "Testigo", "witness_id": "001",
        "_save": "Guardar",
    }
    body.update(overrides)
    return body


def _post(client, op, contract, **overrides):
    if op == "change":
        return client.post(reverse("admin:loans_contract_change", args=[contract.pk]),
                           _change_body(contract, **overrides))
    if op == "delete":
        return client.post(reverse("admin:loans_contract_delete", args=[contract.pk]), {"post": "yes"})
    return client.post(reverse("admin:loans_contract_changelist"), {
        "action": "delete_selected", "_selected_action": [str(contract.pk)], "post": "yes",
    })


def _assert_intact(contract, status="pending_signature", content="texto firmado"):
    from apps.loans.models_contracts import Contract

    fresh = Contract.objects.get(pk=contract.pk)
    assert fresh.status == status
    assert fresh.content == content
    assert fresh.notes == "nota vieja"
    assert fresh.customer_signed_at == contract.customer_signed_at
    assert fresh.officer_signed_at == contract.officer_signed_at
    return fresh


# --- rol: viewer/cashier con permisos de contrato no escriben (la API les da 403) ------------

ROLES = pytest.mark.parametrize("role", ["viewer", "cashier"])


@ROLES
@pytest.mark.parametrize("op", ["change", "delete"])
def test_role_without_manage_loans_gets_403(user_factory, loan_factory, template, role, op):
    client = _client(_staff(user_factory, role, CONTRACT_PERMS))
    contract = _contract(_pending_loan(loan_factory), template, status="draft")

    response = _post(client, op, contract)

    assert response.status_code == 403
    _assert_intact(contract, status="draft")


@ROLES
def test_role_without_manage_loans_cannot_bulk_delete(user_factory, loan_factory, template, role):
    client = _client(_staff(user_factory, role, CONTRACT_PERMS))
    contract = _contract(_pending_loan(loan_factory), template, status="draft")

    response = _post(client, "bulk_delete", contract)

    # Sin permiso de borrado Django retira la acción: el POST no ejecuta nada.
    assert response.status_code in (200, 302, 403)
    _assert_intact(contract, status="draft")


@ROLES
def test_role_without_manage_loans_cannot_add(user_factory, loan_factory, template, role):
    from apps.loans.models_contracts import Contract

    client = _client(_staff(user_factory, role, CONTRACT_PERMS))
    loan = _pending_loan(loan_factory)

    assert client.get(reverse("admin:loans_contract_add")).status_code == 403
    response = client.post(reverse("admin:loans_contract_add"), {
        "loan": str(loan.pk), "template": str(template.pk), "_save": "Guardar",
    })
    assert response.status_code == 403
    assert not Contract.objects.filter(loan=loan).exists()


@ROLES
def test_role_without_manage_loans_still_views(user_factory, loan_factory, template, role):
    client = _client(_staff(user_factory, role, CONTRACT_PERMS))
    contract = _contract(_pending_loan(loan_factory), template)

    assert client.get(reverse("admin:loans_contract_change", args=[contract.pk])).status_code == 200
    assert client.get(reverse("admin:loans_contract_changelist")).status_code == 200


# --- edición: sólo los campos libres; estado, texto y firmas no se tocan ---------------------

def test_manager_edit_only_saves_the_free_fields(manager_client, loan_factory, template):
    from apps.loans.models_contracts import Contract

    contract = _contract(_pending_loan(loan_factory), template)
    other_loan = _pending_loan(loan_factory)

    with CaptureQueriesContext(connection) as ctx:
        response = _post(manager_client, "change", contract, loan=str(other_loan.pk))

    assert response.status_code == 302
    fresh = Contract.objects.get(pk=contract.pk)
    assert fresh.notes == "nota nueva"
    assert fresh.witness_name == "Testigo"
    assert fresh.status == "pending_signature"
    assert fresh.content == "texto firmado"
    assert fresh.loan_id == contract.loan_id
    assert fresh.customer_signed_at is None
    assert fresh.officer_signed_at is None

    table = Contract._meta.db_table
    updates = [q["sql"] for q in ctx.captured_queries if q["sql"].startswith(f'UPDATE "{table}"')]
    assert len(updates) == 1
    for column in ("status", "content", "loan_id", "customer_signed_at", "officer_signed_at", "pdf_file"):
        assert f'"{column}"' not in updates[0].split(" WHERE ")[0], column
    locks = [i for i, q in enumerate(ctx.captured_queries)
             if f'FROM "{table}"' in q["sql"] and "FOR UPDATE" in q["sql"]]
    assert locks, "la edición no bloquea el contrato"


def test_change_page_only_leaves_the_free_fields_editable(manager_client, loan_factory, template):
    contract = _contract(_pending_loan(loan_factory), template)

    response = manager_client.get(reverse("admin:loans_contract_change", args=[contract.pk]))

    assert response.status_code == 200
    form = response.context["adminform"].form
    assert set(form.fields) == {"special_terms", "notes", "witness_name", "witness_id"}


@pytest.mark.parametrize("terminal", ["cancelled", "completed"])
def test_manager_cannot_edit_a_terminal_contract(manager_client, loan_factory, template, terminal):
    contract = _contract(_pending_loan(loan_factory), template, status=terminal)

    response = _post(manager_client, "change", contract)

    assert response.status_code == 403
    _assert_intact(contract, status=terminal)


def test_edit_refuses_a_contract_cancelled_before_the_lock(manager_client, loan_factory, template, monkeypatch):
    from apps.loans.models_contracts import Contract

    contract = _contract(_pending_loan(loan_factory), template)
    original = Contract.objects.select_for_update

    def _select_for_update(*args, **kwargs):
        # La API cancela el contrato justo antes de que el admin lo bloquee.
        Contract.objects.filter(pk=contract.pk).update(status="cancelled")
        return original(*args, **kwargs)

    monkeypatch.setattr(Contract.objects, "select_for_update", _select_for_update)

    response = _post(manager_client, "change", contract, status="pending_signature",
                     customer_signed_at_0="", customer_signed_at_1="",
                     officer_signed_at_0="", officer_signed_at_1="")

    assert response.status_code == 403
    # La cancelación simulada corre en la misma transacción y se deshace con el rechazo: lo que
    # importa es que el admin no escribió nada.
    _assert_intact(contract)


def test_manager_add_ignores_status_content_and_signatures(manager_client, loan_factory, template, user_factory):
    from apps.loans.models_contracts import Contract

    loan = _pending_loan(loan_factory)
    now = timezone.localtime()
    response = manager_client.post(reverse("admin:loans_contract_add"), {
        "loan": str(loan.pk), "template": str(template.pk), "status": "active", "content": "INVENTADO",
        "customer_signed_at_0": now.strftime("%Y-%m-%d"), "customer_signed_at_1": now.strftime("%H:%M:%S"),
        "special_terms": "", "notes": "alta", "witness_name": "", "witness_id": "", "_save": "Guardar",
    })

    assert response.status_code == 302
    contract = Contract.objects.get(loan=loan)
    assert contract.status == "draft"
    assert contract.content == f"Préstamo {loan.loan_number}"
    assert contract.customer_signed_at is None
    assert contract.notes == "alta"


# --- borrado: el mismo predicado que ContractViewSet.perform_destroy -------------------------

DELETE_OPS = pytest.mark.parametrize("op", ["delete", "bulk_delete"])


def _not_deletable(case, loan_factory, template):
    if case == "customer_signed":
        return _contract(_pending_loan(loan_factory), template, customer_signed_at=timezone.now())
    if case == "officer_signed":
        return _contract(_pending_loan(loan_factory), template, officer_signed_at=timezone.now())
    if case == "signed_status":
        return _contract(_pending_loan(loan_factory), template, status="signed")
    if case == "cancelled":
        return _contract(_pending_loan(loan_factory), template, status="cancelled")
    # Borrador sin firmas, pero de un préstamo ya desembolsado.
    return _contract(loan_factory(status="active"), template, status="draft")


@DELETE_OPS
@pytest.mark.parametrize("case", ["customer_signed", "officer_signed", "signed_status", "cancelled", "disbursed"])
def test_manager_cannot_delete_what_the_api_refuses(manager_client, loan_factory, template, op, case):
    from apps.loans.models_contracts import Contract

    contract = _not_deletable(case, loan_factory, template)

    response = _post(manager_client, op, contract)

    assert response.status_code == 403
    assert Contract.objects.filter(pk=contract.pk).exists()


@DELETE_OPS
@pytest.mark.parametrize("status", ["draft", "pending_signature"])
def test_manager_deletes_an_unsigned_contract_of_a_pending_loan(manager_client, loan_factory, template, op, status):
    from apps.loans.models_contracts import Contract, ContractSignatureToken

    contract = _contract(_pending_loan(loan_factory), template, status=status)
    # El enlace de firma pendiente cae con su contrato, como en la API.
    ContractSignatureToken.objects.create(
        contract=contract, token=TOKEN, email="cliente@financiera.test",
        expires_at=timezone.now() + timedelta(days=3),
    )

    with CaptureQueriesContext(connection) as ctx:
        response = _post(manager_client, op, contract)

    assert response.status_code == 302
    assert not Contract.objects.filter(pk=contract.pk).exists()
    assert not ContractSignatureToken.objects.filter(token=TOKEN).exists()
    table = Contract._meta.db_table
    sqls = [q["sql"] for q in ctx.captured_queries]
    locks = [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]
    deletes = [i for i, sql in enumerate(sqls) if sql.startswith(f'DELETE FROM "{table}"')]
    assert locks and deletes and locks[0] < deletes[0]


@DELETE_OPS
def test_delete_refuses_a_contract_signed_before_the_lock(manager_client, loan_factory, template, monkeypatch, op):
    from apps.loans.models_contracts import Contract

    contract = _contract(_pending_loan(loan_factory), template, status="draft")
    original = Contract.objects.select_for_update

    def _select_for_update(*args, **kwargs):
        # El cliente firma por el enlace público justo antes de que el admin bloquee.
        Contract.objects.filter(pk=contract.pk).update(customer_signed_at=timezone.now())
        return original(*args, **kwargs)

    monkeypatch.setattr(Contract.objects, "select_for_update", _select_for_update)

    response = _post(manager_client, op, contract)

    assert response.status_code == 403
    assert Contract.objects.filter(pk=contract.pk).exists()


def test_bulk_delete_with_one_protected_contract_deletes_nothing(manager_client, loan_factory, template):
    from apps.loans.models_contracts import Contract

    loan = _pending_loan(loan_factory)
    draft = _contract(loan, template, status="draft")
    signed = _contract(loan, template, customer_signed_at=timezone.now())

    # Ambos son visibles en la lista; la acción se rechaza por el firmado.
    response = manager_client.post(reverse("admin:loans_contract_changelist"), {
        "action": "delete_selected", "_selected_action": [str(draft.pk), str(signed.pk)], "post": "yes",
    })

    assert response.status_code == 403
    assert Contract.objects.filter(pk__in=[draft.pk, signed.pk]).count() == 2


# --- enlaces de firma: sólo lectura, sin el token ----------------------------------------------

@pytest.fixture
def expired_token(loan_factory, template):
    from apps.loans.models_contracts import ContractSignatureToken

    contract = _contract(_pending_loan(loan_factory), template)
    return ContractSignatureToken.objects.create(
        contract=contract, token=TOKEN, email="cliente@financiera.test",
        expires_at=timezone.now() - timedelta(days=1),
        can_sign_as_customer=True, can_sign_as_officer=False,
    )


@pytest.fixture(params=["cashier", "manager", "superuser"])
def token_client(request, user_factory):
    if request.param == "superuser":
        return _client(user_factory(role="admin", is_staff=True, is_superuser=True))
    return _client(_staff(user_factory, request.param, TOKEN_PERMS))


def test_token_change_page_does_not_show_the_token(token_client, expired_token):
    response = token_client.get(reverse("admin:loans_contractsignaturetoken_change", args=[expired_token.pk]))

    assert response.status_code == 200
    assert TOKEN not in response.content.decode()


def test_token_change_post_is_refused(token_client, expired_token):
    from apps.loans.models_contracts import ContractSignatureToken

    future = timezone.localtime(timezone.now() + timedelta(days=30))
    response = token_client.post(reverse("admin:loans_contractsignaturetoken_change", args=[expired_token.pk]), {
        "contract": str(expired_token.contract_id), "email": "otro@financiera.test",
        "can_sign_as_customer": "on", "can_sign_as_officer": "on",
        "expires_at_0": future.strftime("%Y-%m-%d"), "expires_at_1": future.strftime("%H:%M:%S"),
        "token": "otro-token", "_save": "Guardar",
    })

    assert response.status_code == 403
    fresh = ContractSignatureToken.objects.get(pk=expired_token.pk)
    assert fresh.expires_at == expired_token.expires_at
    assert fresh.can_sign_as_officer is False
    assert fresh.email == "cliente@financiera.test"
    assert fresh.token == TOKEN
    assert not fresh.is_valid


def test_token_search_does_not_match_the_token(token_client, expired_token):
    url = reverse("admin:loans_contractsignaturetoken_changelist")

    assert token_client.get(url, {"q": "cliente@financiera.test"}).context["cl"].result_count == 1
    assert token_client.get(url, {"q": TOKEN}).context["cl"].result_count == 0


def test_token_add_and_delete_are_refused(token_client, expired_token):
    from apps.loans.models_contracts import ContractSignatureToken

    assert token_client.get(reverse("admin:loans_contractsignaturetoken_add")).status_code == 403
    response = token_client.post(
        reverse("admin:loans_contractsignaturetoken_delete", args=[expired_token.pk]), {"post": "yes"}
    )
    assert response.status_code == 403
    response = token_client.post(reverse("admin:loans_contractsignaturetoken_changelist"), {
        "action": "delete_selected", "_selected_action": [str(expired_token.pk)], "post": "yes",
    })
    assert response.status_code in (200, 302, 403)
    assert ContractSignatureToken.objects.filter(pk=expired_token.pk).exists()
