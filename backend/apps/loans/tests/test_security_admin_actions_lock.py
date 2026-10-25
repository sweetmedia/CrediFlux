"""Las acciones masivas del admin (aprobar, rechazar, desembolsar) bloquean cada préstamo.

El changelist no abre transacción: cada acción abre la suya por préstamo, lo bloquea con
SELECT ... FOR UPDATE y vuelve a comprobar el estado sobre la fila bloqueada. Así un préstamo
rechazado, aprobado o editado por la API entre la selección y el guardado no se pisa con la
instancia vieja.
"""
from datetime import date

import pytest
from django.contrib import admin, messages
from django.db import connection
from django.test.utils import CaptureQueriesContext

from .test_security_admin_disburse import _admin_request, _approved_loan, _contract

pytestmark = pytest.mark.django_db


def _admin():
    from apps.loans.admin import LoanAdmin
    from apps.loans.models import Loan

    return LoanAdmin(Loan, admin.site)


def _run(action, user, loans):
    from apps.loans.models import Loan

    request = _admin_request(user)
    getattr(_admin(), action)(request, Loan.objects.filter(pk__in=[loan.pk for loan in loans]))
    return [(m.level, str(m)) for m in messages.get_messages(request)]


def _pending(loan_factory, **overrides):
    return loan_factory(status="pending", disbursement_date=None, **overrides)


def _assert_locked_before_update(ctx):
    from apps.loans.models import Loan

    table = Loan._meta.db_table
    sqls = [q["sql"] for q in ctx.captured_queries]
    locks = [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]
    updates = [i for i, sql in enumerate(sqls) if sql.startswith(f'UPDATE "{table}"')]
    assert locks, "la acción no bloquea los préstamos"
    assert updates
    assert locks[0] < updates[0]
    # El bloqueo va dentro de la transacción propia de la acción (en pytest, un SAVEPOINT).
    savepoints = [i for i, sql in enumerate(sqls) if sql.startswith("SAVEPOINT")]
    assert any(i < locks[0] for i in savepoints), "el bloqueo no va dentro de una transacción"
    return sqls, locks


# (a) orden del bloqueo

@pytest.mark.parametrize("action", ["approve_loans", "reject_loans"])
def test_approve_and_reject_lock_the_loan_before_updating(policy, superuser, loan_factory, action):
    loan = _pending(loan_factory)
    with CaptureQueriesContext(connection) as ctx:
        _run(action, superuser, [loan])

    _assert_locked_before_update(ctx)
    loan.refresh_from_db()
    assert loan.status == ("approved" if action == "approve_loans" else "rejected")


# (b) carrera: el estado cambia entre la selección y el bloqueo

def _flip_before_lock(monkeypatch, loan, **changes):
    from apps.loans.models import Loan

    original = Loan.objects.select_for_update

    def _select_for_update(*args, **kwargs):
        # Otra petición (la API) cambia el préstamo justo antes de que la acción lo bloquee.
        Loan.objects.filter(pk=loan.pk).update(**changes)
        return original(*args, **kwargs)

    monkeypatch.setattr(Loan.objects, "select_for_update", _select_for_update)


def test_approve_does_not_overwrite_a_loan_rejected_meanwhile(
    policy, superuser, user_factory, loan_factory, monkeypatch
):
    other = user_factory(role="admin")
    loan = _pending(loan_factory)
    _flip_before_lock(monkeypatch, loan, status="rejected", rejected_by=other,
                      rejection_date=date(2026, 3, 1))

    sent = _run("approve_loans", superuser, [loan])

    loan.refresh_from_db()
    assert loan.status == "rejected"
    assert loan.approved_by is None
    assert loan.approval_date is None
    assert loan.rejected_by == other
    assert (messages.WARNING, "No hay préstamos pendientes para aprobar") in sent
    assert not [text for level, text in sent if level == messages.SUCCESS]


def test_reject_does_not_overwrite_a_loan_approved_meanwhile(
    policy, superuser, user_factory, loan_factory, monkeypatch
):
    other = user_factory(role="admin")
    loan = _pending(loan_factory)
    _flip_before_lock(monkeypatch, loan, status="approved", approved_by=other,
                      approval_date=date(2026, 3, 1))

    sent = _run("reject_loans", superuser, [loan])

    loan.refresh_from_db()
    assert loan.status == "approved"
    assert loan.rejected_by is None
    assert loan.rejection_date is None
    assert loan.approved_by == other
    assert (messages.WARNING, "No hay préstamos pendientes para rechazar") in sent
    assert not [text for level, text in sent if level == messages.SUCCESS]


# (c) selección mixta

def test_approve_mixed_selection_only_approves_the_pending(
    policy, superuser, user_factory, loan_factory
):
    from django.utils import timezone

    other = user_factory(role="admin")
    pending = [_pending(loan_factory), _pending(loan_factory)]
    already = loan_factory(status="approved", disbursement_date=None,
                           approval_date=date(2026, 3, 1), approved_by=other)

    sent = _run("approve_loans", superuser, pending + [already])

    for loan in pending:
        loan.refresh_from_db()
        assert loan.status == "approved"
        assert loan.approved_by == superuser
        assert loan.approval_date == timezone.localdate()
    already.refresh_from_db()
    assert already.status == "approved"
    assert already.approval_date == date(2026, 3, 1)
    assert already.approved_by == other
    assert (messages.SUCCESS, "2 préstamo(s) aprobado(s) exitosamente") in sent


# (d) desembolso: mismo orden de bloqueo

def test_disburse_locks_the_loan_before_writing(policy, superuser, loan_factory):
    from apps.loans.models import LoanSchedule

    loan = _approved_loan(loan_factory)
    _contract(loan, status="pending_signature", signed=True)

    with CaptureQueriesContext(connection) as ctx:
        sent = _run("disburse_loans", superuser, [loan])

    assert (messages.SUCCESS, "1 préstamo(s) desembolsado(s) exitosamente") in sent
    sqls, locks = _assert_locked_before_update(ctx)
    schedule_table = LoanSchedule._meta.db_table
    inserts = [i for i, sql in enumerate(sqls) if sql.startswith(f'INSERT INTO "{schedule_table}"')]
    assert inserts and locks[0] < inserts[0]
    loan.refresh_from_db()
    assert loan.status == "active"


# --- Fix round 17: las acciones de aprobar/rechazar/desembolsar exigen el rol aprobador -------
# Paridad con la API (CanApproveLoan): superusuario, dueño del tenant o rol admin/manager/
# loan_officer. Sin `permissions=['approve']` cualquier staff con `view_loan` las veía y las
# ejecutaba con un POST al changelist.

ACTIONS = ("approve_loans", "reject_loans", "disburse_loans")
HOST = "tenant.test.localhost"


def _staff_client(user_factory, perms=("view_loan", "change_loan"), **user_kwargs):
    from django.contrib.auth.models import Permission
    from django.test import Client

    user = user_factory(is_staff=True, **user_kwargs)
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="loans", codename__in=perms)
    )
    client = Client(HTTP_HOST=HOST)
    client.force_login(user)
    return user, client


def _changelist_post(client, action, loans):
    from django.urls import reverse

    return client.post(reverse("admin:loans_loan_changelist"), {
        "action": action, "_selected_action": [loan.pk for loan in loans], "index": "0",
    })


@pytest.mark.parametrize("role", ["cashier", "viewer"])
def test_actions_are_hidden_from_staff_without_the_approver_role(
    policy, user_factory, loan_factory, role
):
    from django.urls import reverse

    loan = _pending(loan_factory)
    _, client = _staff_client(user_factory, role=role)

    page = client.get(reverse("admin:loans_loan_changelist"))
    assert page.status_code == 200
    content = page.content.decode()
    assert loan.loan_number in content  # ve el changelist...
    for action in ACTIONS:
        assert f'value="{action}"' not in content  # ...pero no las acciones del ciclo de vida


@pytest.mark.parametrize("role", ["cashier", "viewer"])
def test_forged_lifecycle_actions_have_no_effect_without_the_approver_role(
    policy, user_factory, loan_factory, role
):
    pending = _pending(loan_factory)
    approved = _approved_loan(loan_factory)
    _contract(approved, status="pending_signature", signed=True)
    _, client = _staff_client(user_factory, role=role)

    for action, loan in (("approve_loans", pending), ("reject_loans", pending),
                         ("disburse_loans", approved)):
        response = _changelist_post(client, action, [loan])
        assert response.status_code in (200, 302)

    pending.refresh_from_db()
    assert pending.status == "pending"
    assert pending.approved_by is None and pending.rejected_by is None
    approved.refresh_from_db()
    assert approved.status == "approved"
    assert approved.disbursement_date is None


@pytest.mark.parametrize("user_kwargs", [
    {"role": "loan_officer"},
    {"role": "admin", "is_tenant_owner": True},
])
def test_approver_roles_still_approve_from_the_changelist(policy, user_factory, loan_factory, user_kwargs):
    from django.urls import reverse

    loan = _pending(loan_factory)
    user, client = _staff_client(user_factory, **user_kwargs)

    content = client.get(reverse("admin:loans_loan_changelist")).content.decode()
    for action in ACTIONS:
        assert f'value="{action}"' in content

    response = _changelist_post(client, "approve_loans", [loan])
    assert response.status_code == 302

    loan.refresh_from_db()
    assert loan.status == "approved"
    assert loan.approved_by == user


def test_approver_role_without_change_permission_gets_no_actions(policy, user_factory, loan_factory):
    from django.urls import reverse

    loan = _pending(loan_factory)
    _, client = _staff_client(user_factory, perms=("view_loan",), role="loan_officer")

    content = client.get(reverse("admin:loans_loan_changelist")).content.decode()
    for action in ACTIONS:
        assert f'value="{action}"' not in content
    _changelist_post(client, "approve_loans", [loan])
    loan.refresh_from_db()
    assert loan.status == "pending"
