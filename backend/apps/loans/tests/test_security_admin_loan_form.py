"""El formulario de edición de préstamos del admin no se salta el ciclo de vida (re-auditoría).

Cubre: estado, fechas del ciclo y cuota siempre de solo lectura; deudor y términos de solo
lectura tras aprobar o firmar (misma regla que la API, `loan_terms_locked`); un POST que
fuerza `status` o cambia la tasa de un aprobado no surte efecto; un pendiente sigue
editable; cuotas y pagos no se editan ni borran desde el formulario; sólo se borran
préstamos pendientes o rechazados; y `save_model` rechaza un POST manipulado.
"""
from decimal import Decimal

import pytest
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models.fields.files import FieldFile
from django.forms import MultiWidget
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"

LIFECYCLE = {"status", "approval_date", "disbursement_date", "maturity_date", "payment_amount"}
TERMS = {"customer", "loan_type", "principal_amount", "interest_rate", "term_months",
         "payment_frequency", "first_payment_date", "contract_document"}


@pytest.fixture
def superuser(user_factory):
    return user_factory(role="admin", is_staff=True, is_superuser=True)


@pytest.fixture
def admin_client(superuser):
    client = Client(HTTP_HOST=HOST)
    client.force_login(superuser)
    return client


def _loan_admin():
    from apps.loans.admin import LoanAdmin
    from apps.loans.models import Loan

    return LoanAdmin(Loan, admin.site)


def _request(user):
    request = RequestFactory().get("/admin/loans/loan/", HTTP_HOST=HOST)
    request.user = user
    return request


def _pending(loan_factory, **extra):
    return loan_factory(status="pending", disbursement_date=None, interest_rate=Decimal("1.50"), **extra)


def _post(client, loan, body):
    """POST al formulario de edición; exige que se guarde (302) para que la prueba no sea vacía."""
    response = client.post(_change_url(loan), body)
    errors = None
    if response.status_code != 302 and getattr(response, "context", None):
        errors = [response.context["adminform"].form.errors,
                  [inline.formset.errors for inline in response.context["inline_admin_formsets"]]]
    assert response.status_code == 302, errors
    return response


def _change_url(loan):
    return reverse("admin:loans_loan_change", args=[loan.pk])


def _form_data(response):
    """Cuerpo del POST con los valores que muestra la página de edición (form + inlines)."""
    data = {}

    def put(form, name):
        bound = form[name]
        value = bound.value()
        key = form.add_prefix(name)
        widget = bound.field.widget
        if isinstance(widget, MultiWidget):
            parts = value if isinstance(value, (list, tuple)) else widget.decompress(value)
            for i, part in enumerate(parts):
                data[f"{key}_{i}"] = "" if part is None else str(part)
        elif isinstance(value, bool):
            if value:
                data[key] = "on"
        elif isinstance(value, FieldFile):
            return  # los archivos van en FILES; sin archivo nuevo se conserva el actual
        elif value is None:
            data[key] = ""
        else:
            data[key] = str(value)

    form = response.context["adminform"].form
    for name in form.fields:
        put(form, name)
    for inline in response.context["inline_admin_formsets"]:
        formset = inline.formset
        management = formset.management_form
        for name in management.fields:
            put(management, name)
        for sub in formset.forms:
            for name in sub.fields:
                put(sub, name)
    return data


def _inline_prefix(response, model_name):
    for inline in response.context["inline_admin_formsets"]:
        if inline.formset.model._meta.model_name == model_name:
            return inline.formset.prefix
    raise AssertionError(model_name)


# (a)
def test_readonly_fields_follow_the_lifecycle(superuser, loan_factory):
    model_admin = _loan_admin()
    request = _request(superuser)

    pending = _pending(loan_factory)
    readonly = set(model_admin.get_readonly_fields(request, pending))
    assert LIFECYCLE <= readonly
    assert not (TERMS & readonly)
    assert LIFECYCLE <= set(model_admin.get_readonly_fields(request, None))

    approved = loan_factory(status="approved", disbursement_date=None)
    assert LIFECYCLE | TERMS <= set(model_admin.get_readonly_fields(request, approved))


def test_signed_contract_locks_the_terms_of_a_pending_loan(superuser, loan_factory):
    from apps.loans.models_contracts import Contract

    loan = _pending(loan_factory)
    Contract.objects.create(loan=loan, content="x", status="pending_signature",
                            customer_signed_at=timezone.now())
    assert TERMS <= set(_loan_admin().get_readonly_fields(_request(superuser), loan))


# (b)
def test_status_cannot_be_forced_through_the_change_form(admin_client, superuser, loan_factory):
    loan = _pending(loan_factory, loan_officer=superuser)
    page = admin_client.get(_change_url(loan))
    assert page.status_code == 200
    body = _form_data(page)
    body.update({"status": "active", "disbursement_date": "2026-01-01", "approval_date": "2026-01-01"})

    _post(admin_client, loan, body)

    loan.refresh_from_db()
    assert loan.status == "pending"
    assert loan.disbursement_date is None and loan.approval_date is None


# (c)
def test_terms_of_an_approved_loan_cannot_change_through_the_form(admin_client, superuser, loan_factory):
    loan = loan_factory(status="approved", disbursement_date=None, interest_rate=Decimal("1.50"),
                        loan_officer=superuser)
    page = admin_client.get(_change_url(loan))
    body = _form_data(page)
    body.update({"interest_rate": "9.99", "term_months": "24"})

    _post(admin_client, loan, body)

    loan.refresh_from_db()
    assert (loan.interest_rate, loan.term_months) == (Decimal("1.50"), 6)
    assert loan.status == "approved"


# (d)
def test_pending_loan_terms_stay_editable(admin_client, superuser, loan_factory):
    loan = _pending(loan_factory, loan_officer=superuser)
    page = admin_client.get(_change_url(loan))
    body = _form_data(page)
    body["interest_rate"] = "2.25"

    _post(admin_client, loan, body)

    loan.refresh_from_db()
    assert loan.interest_rate == Decimal("2.25")
    assert loan.status == "pending"
    # La cuota sale del mismo cálculo que la API, nunca del formulario.
    from apps.loans.views import LoanViewSet
    assert loan.payment_amount == LoanViewSet._calculate_payment_amount(loan)


# (e)
def test_schedule_and_payment_rows_are_read_only(admin_client, superuser, active_loan):
    from apps.loans.admin import LoanPaymentInline, LoanScheduleInline
    from apps.loans.models import LoanPayment, LoanSchedule

    for inline_cls, model in ((LoanScheduleInline, LoanSchedule), (LoanPaymentInline, LoanPayment)):
        inline = inline_cls(model, admin.site)
        request = _request(superuser)
        assert not inline.has_add_permission(request, active_loan)
        assert not inline.has_change_permission(request, active_loan)
        assert not inline.has_delete_permission(request, active_loan)

    active_loan.loan_officer = superuser
    active_loan.save(update_fields=["loan_officer"])
    first = LoanSchedule.objects.filter(loan=active_loan).order_by("installment_number").first()
    before = (first.status, first.paid_amount, first.total_amount)
    count = LoanSchedule.objects.filter(loan=active_loan).count()

    page = admin_client.get(_change_url(active_loan))
    body = _form_data(page)
    prefix = _inline_prefix(page, "loanschedule")
    body.update({
        f"{prefix}-0-status": "paid",
        f"{prefix}-0-paid_amount_0": "999999.00",
        f"{prefix}-0-total_amount_0": "1.00",
        f"{prefix}-0-DELETE": "on",
    })

    _post(admin_client, active_loan, body)

    first.refresh_from_db()
    assert (first.status, first.paid_amount, first.total_amount) == before
    assert LoanSchedule.objects.filter(loan=active_loan).count() == count


# (f)
def test_only_pending_or_rejected_loans_can_be_deleted(admin_client, active_loan, loan_factory):
    from apps.loans.models import Loan

    delete_url = reverse("admin:loans_loan_delete", args=[active_loan.pk])
    response = admin_client.post(delete_url, {"post": "yes"})
    assert response.status_code == 403
    assert Loan.objects.filter(pk=active_loan.pk).exists()

    pending = _pending(loan_factory)
    response = admin_client.post(reverse("admin:loans_loan_delete", args=[pending.pk]), {"post": "yes"})
    assert response.status_code == 302
    assert not Loan.objects.filter(pk=pending.pk).exists()


class _CraftedForm:
    def __init__(self, changed):
        self.changed_data = changed


def test_save_model_refuses_crafted_status_or_term_changes(superuser, loan_factory):
    from apps.loans.models import Loan

    model_admin = _loan_admin()
    request = _request(superuser)

    pending = _pending(loan_factory)
    pending.status = "active"
    with pytest.raises(PermissionDenied):
        model_admin.save_model(request, pending, _CraftedForm(["status"]), change=True)
    assert Loan.objects.get(pk=pending.pk).status == "pending"

    approved = loan_factory(status="approved", disbursement_date=None, interest_rate=Decimal("1.50"))
    approved.interest_rate = Decimal("9.99")
    with pytest.raises(PermissionDenied):
        model_admin.save_model(request, approved, _CraftedForm(["interest_rate"]), change=True)
    assert Loan.objects.get(pk=approved.pk).interest_rate == Decimal("1.50")


def test_add_form_creates_a_pending_loan_with_computed_installment(admin_client, superuser, customer_factory):
    from apps.loans.models import Loan
    from apps.loans.views import LoanViewSet

    customer = customer_factory()
    page = admin_client.get(reverse("admin:loans_loan_add"))
    assert page.status_code == 200
    body = _form_data(page)
    body.update({
        "customer": str(customer.pk), "loan_type": "personal", "loan_officer": str(superuser.pk),
        "principal_amount_0": "10000.00", "principal_amount_1": "DOP", "interest_rate": "2.00",
        "term_months": "6", "payment_frequency": "monthly", "first_payment_date": "2026-12-01",
        "status": "active", "payment_amount_0": "1.00", "payment_amount_1": "DOP",
    })

    response = admin_client.post(reverse("admin:loans_loan_add"), body)

    assert response.status_code == 302, response.context and response.context["adminform"].form.errors
    loan = Loan.objects.get(customer=customer)
    assert loan.status == "pending"
    assert loan.payment_amount == LoanViewSet._calculate_payment_amount(loan)
    assert loan.outstanding_balance == loan.principal_amount
