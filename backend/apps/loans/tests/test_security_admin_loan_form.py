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
    from apps.loans.disbursement import calculate_payment_amount
    assert loan.payment_amount == calculate_payment_amount(loan)


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
    def __init__(self, changed, instance=None):
        self.changed_data = changed
        self.instance = instance

    def save_m2m(self):
        pass


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
    from apps.loans.disbursement import calculate_payment_amount

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
    assert loan.payment_amount == calculate_payment_amount(loan)
    assert loan.outstanding_balance == loan.principal_amount


# --- Fix round 4.1 -----------------------------------------------------------------------

def test_late_fees_lock_once_the_loan_is_not_pending(superuser, loan_factory):
    model_admin = _loan_admin()
    request = _request(superuser)
    assert "late_fees" not in model_admin.get_readonly_fields(request, _pending(loan_factory))
    assert "late_fees" in model_admin.get_readonly_fields(request, loan_factory(status="active"))


def test_customer_loan_inline_cannot_change_status_or_principal(admin_client, loan_factory):
    from moneyed import Money

    loan = loan_factory(status="approved", disbursement_date=None)
    customer = loan.customer
    url = reverse("admin:loans_customer_change", args=[customer.pk])
    page = admin_client.get(url)
    assert page.status_code == 200
    body = _form_data(page)
    prefix = _inline_prefix(page, "loan")
    body.update({
        f"{prefix}-0-status": "active",
        f"{prefix}-0-principal_amount_0": "999999.00",
        f"{prefix}-0-principal_amount_1": "DOP",
    })

    response = admin_client.post(url, body)

    assert response.status_code == 302
    loan.refresh_from_db()
    assert loan.status == "approved"
    assert loan.principal_amount == Money(Decimal("10000.00"), "DOP")


def test_schedule_and_payment_admins_are_read_only(admin_client, superuser, active_loan):
    from moneyed import Money
    from apps.loans.models import LoanPayment, LoanSchedule

    row = LoanSchedule.objects.filter(loan=active_loan).order_by("installment_number").first()
    before = (row.status, row.paid_amount, row.total_amount)
    response = admin_client.post(
        reverse("admin:loans_loanschedule_change", args=[row.pk]),
        {"loan": str(active_loan.pk), "installment_number": "1", "due_date": "2026-01-01",
         "status": "paid", "total_amount_0": "1.00", "total_amount_1": "DOP",
         "principal_amount_0": "1.00", "principal_amount_1": "DOP",
         "interest_amount_0": "0.00", "interest_amount_1": "DOP",
         "paid_amount_0": "1.00", "paid_amount_1": "DOP"},
    )
    assert response.status_code == 403
    row.refresh_from_db()
    assert (row.status, row.paid_amount, row.total_amount) == before
    assert admin_client.get(reverse("admin:loans_loanschedule_change", args=[row.pk])).status_code == 200

    payment = LoanPayment.objects.create(
        loan=active_loan, amount=Money(Decimal("500.00"), "DOP"),
        payment_method="bank_transfer", status="completed", created_by=superuser,
    )
    response = admin_client.post(
        reverse("admin:loans_loanpayment_change", args=[payment.pk]),
        {"loan": str(active_loan.pk), "payment_date": "2026-01-01", "status": "reversed",
         "amount_0": "1.00", "amount_1": "DOP", "payment_method": "cash"},
    )
    assert response.status_code == 403
    payment.refresh_from_db()
    assert (payment.status, payment.amount) == ("completed", Money(Decimal("500.00"), "DOP"))
    assert admin_client.post(
        reverse("admin:loans_loanpayment_delete", args=[payment.pk]), {"post": "yes"}
    ).status_code == 403
    assert LoanPayment.objects.filter(pk=payment.pk).exists()
    assert admin_client.get(reverse("admin:loans_loanpayment_add")).status_code == 403


def _collateral(loan):
    from moneyed import Money
    from apps.loans.models import Collateral

    return Collateral.objects.create(
        loan=loan, collateral_type="vehicle", description="Carro",
        estimated_value=Money(Decimal("5000.00"), "DOP"),
    )


def _collateral_body(collateral, description):
    return {
        "loan": str(collateral.loan_id), "collateral_type": "vehicle", "description": description,
        "status": "active", "estimated_value_0": "5000.00", "estimated_value_1": "DOP",
        "appraisal_value_0": "", "appraisal_value_1": "DOP", "appraisal_date": "", "notes": "",
    }


def test_collateral_admin_follows_the_loan_lifecycle(admin_client, active_loan, loan_factory):
    from apps.loans.models import Collateral

    locked = _collateral(active_loan)
    url = reverse("admin:loans_collateral_change", args=[locked.pk])
    assert admin_client.post(url, _collateral_body(locked, "Cambiada")).status_code == 403
    locked.refresh_from_db()
    assert locked.description == "Carro"
    assert admin_client.post(
        reverse("admin:loans_collateral_delete", args=[locked.pk]), {"post": "yes"}
    ).status_code == 403
    assert Collateral.objects.filter(pk=locked.pk).exists()

    # Alta contra un préstamo activo: el préstamo no es elegible y no se crea.
    body = _collateral_body(locked, "Nueva")
    admin_client.post(reverse("admin:loans_collateral_add"), body)
    assert not Collateral.objects.filter(description="Nueva").exists()

    editable = _collateral(_pending(loan_factory))
    url = reverse("admin:loans_collateral_change", args=[editable.pk])
    response = admin_client.post(url, _collateral_body(editable, "Cambiada"))
    assert response.status_code == 302, response.context and response.context["adminform"].form.errors
    editable.refresh_from_db()
    assert editable.description == "Cambiada"


def test_admin_applies_the_origination_policy(admin_client, superuser, tenant_schema, loan_factory):
    """La violación de política en la edición vuelve al formulario con el error (no 403)."""
    original = tenant_schema.max_interest_rate
    tenant_schema.max_interest_rate = Decimal("36.00")
    tenant_schema.save()
    try:
        loan = _pending(loan_factory, loan_officer=superuser)
        page = admin_client.get(_change_url(loan))
        body = _form_data(page)
        body["interest_rate"] = "9.00"  # 108 % anual > 36 %
        response = admin_client.post(_change_url(loan), body)
        assert response.status_code == 200
        assert "excede el máximo anual" in str(response.context["adminform"].form.errors["interest_rate"])
        loan.refresh_from_db()
        assert loan.interest_rate == Decimal("1.50")
    finally:
        tenant_schema.max_interest_rate = original
        tenant_schema.save()


# --- Fix round 6: la política se informa como errores del formulario ---------------------

def test_add_form_reports_rate_above_policy_as_field_error(admin_client, superuser, tenant_schema,
                                                           customer_factory):
    from apps.loans.models import Loan

    original = tenant_schema.max_interest_rate
    tenant_schema.max_interest_rate = Decimal("36.00")
    tenant_schema.save()
    try:
        customer = customer_factory()
        page = admin_client.get(reverse("admin:loans_loan_add"))
        body = _form_data(page)
        body.update({
            "customer": str(customer.pk), "loan_type": "personal", "loan_officer": str(superuser.pk),
            "principal_amount_0": "10000.00", "principal_amount_1": "DOP", "interest_rate": "5.00",
            "term_months": "6", "payment_frequency": "monthly", "first_payment_date": "2026-12-01",
        })

        response = admin_client.post(reverse("admin:loans_loan_add"), body)

        assert response.status_code == 200
        errors = response.context["adminform"].form.errors
        assert "excede el máximo anual de 36.00%" in str(errors["interest_rate"])
        assert "excede el máximo anual" in response.content.decode()
        assert not Loan.objects.filter(customer=customer).exists()
    finally:
        tenant_schema.max_interest_rate = original
        tenant_schema.save()


def test_change_form_reports_principal_above_policy_as_field_error(admin_client, superuser,
                                                                    tenant_schema, loan_factory):
    from moneyed import Money

    original = tenant_schema.max_loan_amount
    tenant_schema.max_loan_amount = Money(Decimal("50000.00"), "DOP")
    tenant_schema.save()
    try:
        loan = _pending(loan_factory, loan_officer=superuser)
        before = (loan.principal_amount, loan.payment_amount)
        page = admin_client.get(_change_url(loan))
        body = _form_data(page)
        body["principal_amount_0"] = "999999.00"

        response = admin_client.post(_change_url(loan), body)

        assert response.status_code == 200
        errors = response.context["adminform"].form.errors
        assert "según la política de la organización" in str(errors["principal_amount"])
        loan.refresh_from_db()
        assert (loan.principal_amount, loan.payment_amount) == before
        assert loan.status == "pending"
    finally:
        tenant_schema.max_loan_amount = original
        tenant_schema.save()


def test_contract_document_alone_does_not_regenerate_the_contract(superuser, loan_factory):
    from apps.loans.models_contracts import Contract, ContractTemplate

    loan = _pending(loan_factory)
    # Con plantilla: si el documento disparara la regeneración, el contenido cambiaría a "regenerado".
    template = ContractTemplate.objects.create(name="Base", content="regenerado", is_active=True, is_default=True)
    contract = Contract.objects.create(
        loan=loan, template=template, content="original", status="pending_signature"
    )
    before_payment = loan.payment_amount
    form = _CraftedForm(["contract_document"], instance=loan)
    model_admin = _loan_admin()
    model_admin.save_model(_request(superuser), loan, form, change=True)
    model_admin.save_related(_request(superuser), form, [], change=True)
    contract.refresh_from_db()
    loan.refresh_from_db()
    assert contract.content == "original"
    assert loan.payment_amount == before_payment


def test_bulk_delete_action_respects_the_lifecycle(admin_client, active_loan, loan_factory):
    from apps.loans.models import Collateral, Loan

    pending = _pending(loan_factory)
    admin_client.post(reverse("admin:loans_loan_changelist"), {
        "action": "delete_selected", "_selected_action": [active_loan.pk, pending.pk], "post": "yes",
    })
    assert Loan.objects.filter(pk=active_loan.pk).exists()
    assert Loan.objects.filter(pk=pending.pk).exists()

    locked = _collateral(active_loan)
    admin_client.post(reverse("admin:loans_collateral_changelist"), {
        "action": "delete_selected", "_selected_action": [locked.pk], "post": "yes",
    })
    assert Collateral.objects.filter(pk=locked.pk).exists()

    admin_client.post(reverse("admin:loans_loan_changelist"), {
        "action": "delete_selected", "_selected_action": [pending.pk], "post": "yes",
    })
    assert not Loan.objects.filter(pk=pending.pk).exists()


# --- Respaldos de save_model que el formulario ya no alcanza con entrada honesta -------------

def test_save_model_backstop_still_refuses_policy_violations(superuser, tenant_schema, loan_factory):
    """Un POST manipulado que esquiva el formulario sigue chocando con la política en save_model."""
    from apps.loans.models import Loan

    original = tenant_schema.max_interest_rate
    tenant_schema.max_interest_rate = Decimal("36.00")
    tenant_schema.save()
    try:
        loan = _pending(loan_factory)
        loan.interest_rate = Decimal("9.00")  # 108 % anual > 36 %
        with pytest.raises(PermissionDenied):
            _loan_admin().save_model(_request(superuser), loan, _CraftedForm(["interest_rate"]), change=True)
        assert Loan.objects.get(pk=loan.pk).interest_rate == Decimal("1.50")
    finally:
        tenant_schema.max_interest_rate = original
        tenant_schema.save()


def test_save_model_refuses_crafted_late_fees_on_a_live_loan(superuser, loan_factory):
    from apps.loans.models import Loan
    from moneyed import Money

    loan = loan_factory(status="active")
    before = Loan.objects.get(pk=loan.pk).late_fees
    loan.late_fees = Money("999.00", "DOP")
    with pytest.raises(PermissionDenied):
        _loan_admin().save_model(_request(superuser), loan, _CraftedForm(["late_fees"]), change=True)
    assert Loan.objects.get(pk=loan.pk).late_fees == before


# --- Fix round 7: el préstamo creado en el admin nace con su contrato, igual que en la API ---

def _post_add_form(admin_client, superuser, customer, collateral=None, **extra):
    page = admin_client.get(reverse("admin:loans_loan_add"))
    assert page.status_code == 200
    body = _form_data(page)
    body.update({
        "customer": str(customer.pk), "loan_type": "personal", "loan_officer": str(superuser.pk),
        "principal_amount_0": "10000.00", "principal_amount_1": "DOP", "interest_rate": "2.00",
        "term_months": "6", "payment_frequency": "monthly", "first_payment_date": "2026-12-01",
        "payment_amount_0": "1.00", "payment_amount_1": "DOP",
    })
    if collateral:
        _add_collateral_row(body, _inline_prefix(page, "collateral"), collateral)
    return admin_client.post(reverse("admin:loans_loan_add"), body, **extra)


def _add_collateral_row(body, prefix, description):
    """Agrega una fila nueva al inline de garantías del cuerpo del POST."""
    index = int(body[f"{prefix}-TOTAL_FORMS"])
    body[f"{prefix}-TOTAL_FORMS"] = str(index + 1)
    body.update({
        f"{prefix}-{index}-collateral_type": "vehicle",
        f"{prefix}-{index}-description": description,
        f"{prefix}-{index}-estimated_value_0": "50000.00",
        f"{prefix}-{index}-estimated_value_1": "DOP",
        f"{prefix}-{index}-status": "active",
    })


def test_add_form_generates_the_initial_contract_from_the_default_template(
    admin_client, superuser, customer_factory
):
    from apps.loans.models import Loan
    from apps.loans.models_contracts import Contract, ContractTemplate

    template = ContractTemplate.objects.create(
        name="Base", content="Préstamo {{loan_number}} tasa {{interest_rate}}", is_active=True, is_default=True
    )
    customer = customer_factory()

    response = _post_add_form(admin_client, superuser, customer)

    assert response.status_code == 302, response.context and response.context["adminform"].form.errors
    loan = Loan.objects.get(customer=customer)
    assert loan.status == "pending"
    contract = Contract.objects.get(loan=loan)
    assert contract.status == "pending_signature"
    assert contract.generated_by == superuser
    assert contract.template == template
    assert contract.content == f"Préstamo {loan.loan_number} tasa 2.00%"


def test_add_form_without_template_creates_the_loan_and_warns(admin_client, superuser, customer_factory):
    from apps.loans.models import Loan
    from apps.loans.models_contracts import Contract, ContractTemplate

    ContractTemplate.objects.update(is_active=False)
    customer = customer_factory()

    response = _post_add_form(admin_client, superuser, customer, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain, response.context and response.context["adminform"].form.errors
    loan = Loan.objects.get(customer=customer)
    assert loan.status == "pending"
    assert not Contract.objects.filter(loan=loan).exists()
    warnings = [str(m) for m in response.context["messages"] if m.level_tag == "warning"]
    assert any("plantilla de contrato" in m for m in warnings), warnings


def test_add_form_rolls_back_the_loan_if_the_contract_fails(
    admin_client, superuser, customer_factory, monkeypatch
):
    """Un fallo distinto de "no hay plantilla" deshace también el préstamo (transacción del admin)."""
    from apps.loans import utils_contracts
    from apps.loans.models import Loan
    from apps.loans.models_contracts import ContractTemplate

    ContractTemplate.objects.create(name="Base", content="x", is_active=True, is_default=True)

    def boom(*args, **kwargs):
        raise RuntimeError("falla al renderizar")

    monkeypatch.setattr(utils_contracts, "replace_contract_variables", boom)
    customer = customer_factory()

    with pytest.raises(RuntimeError):
        _post_add_form(admin_client, superuser, customer)

    assert not Loan.objects.filter(customer=customer).exists()


# --- Fix round 7.1: el contrato se arma después de guardar las garantías del inline ----------

def test_add_form_contract_includes_collateral_from_the_inline(admin_client, superuser, customer_factory):
    from apps.loans.models import Loan
    from apps.loans.models_contracts import Contract, ContractTemplate

    ContractTemplate.objects.create(
        name="Base", content="Garantías: {{collateral_description}}", is_active=True, is_default=True
    )
    customer = customer_factory()

    response = _post_add_form(admin_client, superuser, customer, collateral="Toyota Corolla 2020")

    assert response.status_code == 302, response.context and response.context["adminform"].form.errors
    loan = Loan.objects.get(customer=customer)
    assert loan.collaterals.count() == 1
    contract = Contract.objects.get(loan=loan)
    assert "Toyota Corolla 2020" in contract.content
    assert "Sin garantías" not in contract.content


def test_change_form_adding_collateral_regenerates_the_pending_contract(
    admin_client, superuser, loan_factory
):
    from apps.loans.models_contracts import Contract, ContractTemplate

    template = ContractTemplate.objects.create(
        name="Base", content="Garantías: {{collateral_description}}", is_active=True, is_default=True
    )
    loan = _pending(loan_factory, loan_officer=superuser)
    contract = Contract.objects.create(
        loan=loan, template=template, content="Garantías: Sin garantías", status="pending_signature"
    )
    page = admin_client.get(_change_url(loan))
    body = _form_data(page)
    _add_collateral_row(body, _inline_prefix(page, "collateral"), "Honda Civic 2019")

    _post(admin_client, loan, body)

    assert loan.collaterals.count() == 1
    contract.refresh_from_db()
    assert "Honda Civic 2019" in contract.content
    assert "Sin garantías" not in contract.content


# --- Borrado masivo de préstamos: guarda y borrado en una sola transacción con bloqueo ------


def _bulk_delete_loans(client, loans):
    return client.post(reverse("admin:loans_loan_changelist"), {
        "action": "delete_selected", "_selected_action": [loan.pk for loan in loans], "post": "yes",
    })


def _pending_contract(loan):
    from apps.loans.models_contracts import Contract

    return Contract.objects.create(loan=loan, content="x", status="pending_signature")


def test_bulk_delete_locks_the_loans_before_deleting(admin_client, loan_factory):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    from apps.loans.models import Loan

    table = Loan._meta.db_table
    loan = _pending(loan_factory)
    with CaptureQueriesContext(connection) as ctx:
        response = _bulk_delete_loans(admin_client, [loan])

    assert response.status_code == 302
    assert not Loan.objects.filter(pk=loan.pk).exists()
    sqls = [q["sql"] for q in ctx.captured_queries]
    locks = [i for i, sql in enumerate(sqls) if f'"{table}"' in sql and "FOR UPDATE" in sql]
    deletes = [i for i, sql in enumerate(sqls) if sql.startswith(f'DELETE FROM "{table}"')]
    assert locks, "el borrado masivo no bloquea los préstamos"
    assert deletes
    assert locks[0] < deletes[0]
    # El bloqueo va dentro de la transacción propia del admin (en pytest aparece como SAVEPOINT);
    # sin ella, select_for_update fallaría en producción con TransactionManagementError.
    savepoints = [i for i, sql in enumerate(sqls) if sql.startswith("SAVEPOINT")]
    assert any(i < locks[0] for i in savepoints), "el bloqueo no va dentro de una transacción"


def test_bulk_delete_of_mixed_statuses_deletes_nothing(admin_client, active_loan, loan_factory):
    from apps.loans.models import Collateral, Loan
    from apps.loans.models_contracts import Contract

    pending = _pending(loan_factory)
    collateral = _collateral(pending)
    contract = _pending_contract(pending)

    response = _bulk_delete_loans(admin_client, [pending, active_loan])

    assert response.status_code == 403
    assert Loan.objects.filter(pk__in=[pending.pk, active_loan.pk]).count() == 2
    assert Collateral.objects.filter(pk=collateral.pk).exists()
    assert Contract.objects.filter(pk=contract.pk).exists()


def test_bulk_delete_of_pending_loans_cascades(admin_client, loan_factory):
    from apps.loans.models import Collateral, Loan
    from apps.loans.models_contracts import Contract

    loans = [_pending(loan_factory), _pending(loan_factory)]
    collaterals = [_collateral(loan).pk for loan in loans]
    contracts = [_pending_contract(loan).pk for loan in loans]

    response = _bulk_delete_loans(admin_client, loans)

    assert response.status_code == 302
    assert not Loan.objects.filter(pk__in=[loan.pk for loan in loans]).exists()
    assert not Collateral.objects.filter(pk__in=collaterals).exists()
    assert not Contract.objects.filter(pk__in=contracts).exists()


# --- Fix round 17: formulario, borrado individual e inline deciden sobre el préstamo bloqueado ---
# Simulación en una sola conexión (como test_security_admin_actions_lock.py): otra petición
# cambia el préstamo justo antes de que el admin lo bloquee con SELECT ... FOR UPDATE.


def _change_before_lock(monkeypatch, change, on_call=1):
    """Ejecuta `change()` justo antes de la llamada número `on_call` a Loan.objects.select_for_update."""
    from apps.loans.models import Loan

    original = Loan.objects.select_for_update
    calls = {"n": 0}

    def _select_for_update(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == on_call:
            change()
        return original(*args, **kwargs)

    monkeypatch.setattr(Loan.objects, "select_for_update", _select_for_update)
    return calls


def _approve_meanwhile(loan, approver):
    from datetime import date
    from apps.loans.models import Loan

    def change():
        Loan.objects.filter(pk=loan.pk).update(
            status="approved", approval_date=date(2026, 3, 1), approved_by=approver,
        )
    return change


def test_change_form_does_not_undo_a_disbursement_made_meanwhile(
    admin_client, superuser, user_factory, loan_factory, monkeypatch
):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    from apps.loans.disbursement import apply_disbursement
    from apps.loans.models import Loan, LoanSchedule
    from .test_security_admin_disburse import _contract

    other = user_factory(role="admin")
    loan = _pending(loan_factory, loan_officer=superuser, notes="antes")
    contract = _contract(loan, status="pending_signature", signed=True)
    page = admin_client.get(_change_url(loan))
    body = _form_data(page)
    body["notes"] = "nota nueva"

    def disburse():
        # La API aprueba y desembolsa mientras el formulario (sólo notas) se envía.
        _approve_meanwhile(loan, other)()
        apply_disbursement(Loan.objects.get(pk=loan.pk), contract)

    _change_before_lock(monkeypatch, disburse)
    with CaptureQueriesContext(connection) as ctx:
        _post(admin_client, loan, body)

    loan.refresh_from_db()
    assert loan.status == "active"
    assert loan.disbursement_date is not None
    assert loan.approved_by == other
    assert loan.notes == "nota nueva"
    assert LoanSchedule.objects.filter(loan=loan).exists()
    contract.refresh_from_db()
    assert contract.status == "active"

    table = Loan._meta.db_table
    sqls = [q["sql"] for q in ctx.captured_queries]
    locks = [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]
    assert locks, "el formulario no bloquea el préstamo"
    admin_updates = [sqls[i] for i in range(locks[0] + 1, len(sqls)) if sqls[i].startswith(f'UPDATE "{table}"')]
    assert admin_updates, "el formulario no guardó el préstamo después del bloqueo"
    for sql in admin_updates:
        set_clause = sql.split(" WHERE ")[0]
        assert '"notes"' in set_clause
        assert '"status"' not in set_clause
        assert '"disbursement_date"' not in set_clause
        assert '"outstanding_balance"' not in set_clause


def test_change_form_term_edit_refused_when_loan_approved_meanwhile(
    admin_client, superuser, user_factory, loan_factory, monkeypatch
):
    from apps.loans.models import Loan

    other = user_factory(role="admin")
    loan = _pending(loan_factory, loan_officer=superuser)
    page = admin_client.get(_change_url(loan))
    body = _form_data(page)
    body["interest_rate"] = "2.25"

    _change_before_lock(monkeypatch, _approve_meanwhile(loan, other))
    response = admin_client.post(_change_url(loan), body)

    assert response.status_code == 403
    current = Loan.objects.get(pk=loan.pk)
    # El 403 deshace la transacción de changeform_view; en esta simulación de una sola conexión
    # eso incluye el cambio "concurrente". Lo que importa: la tasa no se escribió.
    assert current.interest_rate == Decimal("1.50")


def test_single_delete_refused_when_loan_approved_meanwhile(
    admin_client, user_factory, loan_factory, monkeypatch
):
    from apps.loans.models import Loan

    other = user_factory(role="admin")
    loan = _pending(loan_factory)
    collateral = _collateral(loan)

    _change_before_lock(monkeypatch, _approve_meanwhile(loan, other))
    response = admin_client.post(reverse("admin:loans_loan_delete", args=[loan.pk]), {"post": "yes"})

    assert response.status_code == 403
    assert Loan.objects.filter(pk=loan.pk).exists()  # el 403 deshace también la simulación
    assert loan.collaterals.filter(pk=collateral.pk).exists()


def test_single_delete_of_a_pending_loan_locks_and_deletes(admin_client, loan_factory):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    from apps.loans.models import Loan

    table = Loan._meta.db_table
    loan = _pending(loan_factory)
    with CaptureQueriesContext(connection) as ctx:
        response = admin_client.post(reverse("admin:loans_loan_delete", args=[loan.pk]), {"post": "yes"})

    assert response.status_code == 302
    assert not Loan.objects.filter(pk=loan.pk).exists()
    sqls = [q["sql"] for q in ctx.captured_queries]
    locks = [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]
    deletes = [i for i, sql in enumerate(sqls) if sql.startswith(f'DELETE FROM "{table}"')]
    assert locks and deletes and locks[0] < deletes[0]


def test_collateral_inline_refused_when_loan_approved_meanwhile(
    admin_client, superuser, user_factory, loan_factory, monkeypatch
):
    from apps.loans.models import Collateral, Loan
    from apps.loans.models_contracts import Contract, ContractTemplate

    template = ContractTemplate.objects.create(
        name="Base", content="Garantías: {{collateral_description}}", is_active=True, is_default=True
    )
    other = user_factory(role="admin")
    loan = _pending(loan_factory, loan_officer=superuser)
    contract = Contract.objects.create(
        loan=loan, template=template, content="Garantías: Sin garantías", status="pending_signature"
    )
    page = admin_client.get(_change_url(loan))
    body = _form_data(page)
    _add_collateral_row(body, _inline_prefix(page, "collateral"), "Honda Civic 2019")

    # Primera llamada: el bloqueo de save_model (aún pendiente). Segunda: el del inline de garantías.
    calls = _change_before_lock(monkeypatch, _approve_meanwhile(loan, other), on_call=2)
    response = admin_client.post(_change_url(loan), body)

    assert response.status_code == 403
    assert calls["n"] == 2  # lo rechazó el bloqueo del inline, no el de save_model
    assert Loan.objects.filter(pk=loan.pk).exists()  # el 403 deshace también la simulación
    assert not Collateral.objects.filter(loan=loan).exists()
    contract.refresh_from_db()
    assert contract.content == "Garantías: Sin garantías"
