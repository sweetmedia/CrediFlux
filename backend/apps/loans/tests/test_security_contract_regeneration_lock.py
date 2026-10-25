"""La regeneración del contrato decide y escribe sobre el contrato bloqueado (ronda 16).

regenerate_latest_loan_contract leía el último contrato con un SELECT sin bloqueo, rehusaba sólo
si esa foto ya tenía firma y luego escribía el contenido. Las firmas (sign_customer, sign_officer,
la firma pública) bloquean sólo el contrato: con una firma en curso, la regeneración lo veía sin
firmar, su UPDATE esperaba el bloqueo del firmante y luego reescribía el texto ya firmado.
Además no rehusaba contratos cancelados o completados sin firma, a diferencia de
ContractViewSet.regenerate. Ahora el contrato se bloquea (SELECT ... FOR UPDATE, después del
préstamo: orden préstamo → fila → contrato → token) y se decide sobre la fila bloqueada.
"""
import pytest
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from .test_security_admin_related_regeneration import (  # noqa: F401  (template es fixture)
    _contract, _pending, template,
)
from .test_security_api_related_lifecycle import (  # noqa: F401  (api es fixture)
    _loan_locks, _request, _row, api,
)

pytestmark = pytest.mark.django_db


def _contract_table():
    from apps.loans.models_contracts import Contract

    return Contract._meta.db_table


# (a) orden: préstamo bloqueado → contrato bloqueado → UPDATE del contrato

def test_collateral_patch_locks_the_contract_before_rewriting_it(tenant_schema, api, template, loan_factory):
    loan = _pending(loan_factory)
    row = _row("collateral", loan)
    contract = _contract(loan, template)
    table = _contract_table()

    with CaptureQueriesContext(connection) as ctx:
        response = _request(api, "collateral", "update", loan, row, name="Moto")
    assert response.status_code == 200, response.content

    sqls = [q["sql"] for q in ctx.captured_queries]
    loan_locks = _loan_locks(sqls)
    contract_locks = [
        i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql
    ]
    contract_updates = [i for i, sql in enumerate(sqls) if sql.startswith(f'UPDATE "{table}"')]
    assert loan_locks, "la API no bloquea el préstamo"
    assert contract_locks, "la regeneración no bloquea el contrato"
    assert contract_updates, "la regeneración no reescribió el contrato"
    assert loan_locks[0] < contract_locks[0] < contract_updates[0]
    # Sólo se bloquea la fila del contrato (of=self), no tablas unidas.
    assert all(f'FOR UPDATE OF "{table}"' in sqls[i] for i in contract_locks)
    contract.refresh_from_db()
    assert "Moto" in contract.content


# (b) carrera: una firma o una cancelación confirmada justo antes del bloqueo del contrato

def _change_contract_before_lock(monkeypatch, contract, **changes):
    from apps.loans.models_contracts import Contract

    original = Contract.objects.select_for_update
    calls = []

    def _select_for_update(*args, **kwargs):
        if not calls:
            Contract.objects.filter(pk=contract.pk).update(**changes)
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(Contract.objects, "select_for_update", _select_for_update)
    return calls


@pytest.mark.parametrize("changes", [
    pytest.param({"customer_signed_at": "now"}, id="firma-cliente"),
    pytest.param({"officer_signed_at": "now"}, id="firma-oficial"),
    pytest.param({"status": "cancelled"}, id="cancelado"),
])
def test_regeneration_after_a_concurrent_change_is_a_no_op(
    tenant_schema, api, template, loan_factory, monkeypatch, changes
):
    loan = _pending(loan_factory)
    row = _row("collateral", loan)
    contract = _contract(loan, template)
    changes = {k: (timezone.now() if v == "now" else v) for k, v in changes.items()}
    calls = _change_contract_before_lock(monkeypatch, contract, **changes)

    response = _request(api, "collateral", "update", loan, row, name="Moto")

    assert response.status_code == 200, response.content
    assert calls, "la regeneración no pasó por el bloqueo del contrato"
    row.refresh_from_db()
    assert row.description == "Moto"
    contract.refresh_from_db()
    assert contract.content == "texto viejo", "se reescribió un contrato firmado o cancelado"


# El helper rehúsa por estado aunque no haya marcas de firma (igual que ContractViewSet.regenerate).

@pytest.mark.parametrize("status", ["signed", "active", "completed", "cancelled"])
def test_regeneration_skips_closed_contracts_by_status(tenant_schema, template, loan_factory, status):
    from apps.loans.utils_contracts import regenerate_latest_loan_contract

    loan = _pending(loan_factory)
    contract = _contract(loan, template)
    type(contract).objects.filter(pk=contract.pk).update(status=status)

    with transaction.atomic():
        assert regenerate_latest_loan_contract(loan) is None

    contract.refresh_from_db()
    assert contract.content == "texto viejo"


# (c) regresión: un contrato por firmar sin firmas se sigue reescribiendo

def test_regeneration_still_rewrites_an_unsigned_pending_contract(tenant_schema, template, loan_factory):
    from apps.loans.utils_contracts import regenerate_latest_loan_contract

    loan = _pending(loan_factory)
    _row("collateral", loan, "Camión")
    contract = _contract(loan, template)

    with transaction.atomic():
        result = regenerate_latest_loan_contract(loan)

    assert result is not None and result.pk == contract.pk
    contract.refresh_from_db()
    assert "Camión" in contract.content
