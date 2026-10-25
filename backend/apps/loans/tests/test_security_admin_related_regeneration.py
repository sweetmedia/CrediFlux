"""Los admins independientes de garantías y garantes rehacen el contrato por firmar (ronda 8).

El contrato pendiente embebe las garantías (`{{collateral_description}}`) y el primer garante
(`{{guarantor_name}}`). La API lo regenera al crear/editar esas filas y el formulario del
préstamo también; aquí se cubre que los admins de Collateral y Guarantor hagan lo mismo al
agregar, editar, mover o borrar (uno a uno o con la acción masiva), y que un contrato firmado
no se reescriba.
"""
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"
TEMPLATE = "Garantías: {{collateral_description}} | Garante: {{guarantor_name}}"


@pytest.fixture
def superuser(user_factory):
    return user_factory(role="admin", is_staff=True, is_superuser=True)


@pytest.fixture
def admin_client(superuser):
    client = Client(HTTP_HOST=HOST)
    client.force_login(superuser)
    return client


@pytest.fixture
def template():
    from apps.loans.models_contracts import ContractTemplate

    return ContractTemplate.objects.create(name="Base", content=TEMPLATE, is_active=True, is_default=True)


def _pending(loan_factory, **extra):
    return loan_factory(status="pending", disbursement_date=None, interest_rate=Decimal("1.50"), **extra)


def _contract(loan, template, **extra):
    from apps.loans.models_contracts import Contract

    return Contract.objects.create(
        loan=loan, template=template, content="texto viejo", status="pending_signature", **extra
    )


def _collateral(loan, description="Carro"):
    from moneyed import Money
    from apps.loans.models import Collateral

    return Collateral.objects.create(
        loan=loan, collateral_type="vehicle", description=description,
        estimated_value=Money(Decimal("5000.00"), "DOP"),
    )


def _collateral_body(loan_id, description):
    return {
        "loan": str(loan_id), "collateral_type": "vehicle", "description": description,
        "status": "active", "estimated_value_0": "5000.00", "estimated_value_1": "DOP",
        "appraisal_value_0": "", "appraisal_value_1": "DOP", "appraisal_date": "", "notes": "",
    }


def _guarantor(loan, first_name="Pedro", last_name="Gómez"):
    from apps.loans.models_guarantors import Guarantor

    return Guarantor.objects.create(
        loan=loan, first_name=first_name, last_name=last_name, id_type="cedula",
        id_number="00112345678", phone="+18095551234", address="Calle 1",
        relationship="friend", status="active",
    )


def _guarantor_body(loan_id, first_name, last_name="Gómez"):
    return {
        "loan": str(loan_id), "first_name": first_name, "last_name": last_name,
        "id_type": "cedula", "id_number": "00112345678", "date_of_birth": "", "gender": "",
        "phone": "+18095551234", "alternate_phone": "", "email": "", "address": "Calle 1",
        "city": "", "province": "", "employer_name": "", "occupation": "",
        "monthly_income_0": "", "monthly_income_1": "DOP",
        "relationship": "friend", "status": "active", "notes": "",
    }


def _assert_saved(response):
    errors = None
    if response.status_code != 302 and getattr(response, "context", None):
        errors = response.context["adminform"].form.errors
    assert response.status_code == 302, errors


# (a)
def test_collateral_add_regenerates_the_pending_contract(admin_client, template, loan_factory):
    loan = _pending(loan_factory)
    contract = _contract(loan, template)

    _assert_saved(admin_client.post(
        reverse("admin:loans_collateral_add"), _collateral_body(loan.pk, "Toyota Corolla 2020")
    ))

    contract.refresh_from_db()
    assert "Toyota Corolla 2020" in contract.content


# (b)
def test_collateral_change_regenerates_the_pending_contract(admin_client, template, loan_factory):
    loan = _pending(loan_factory)
    collateral = _collateral(loan, "Carro viejo")
    contract = _contract(loan, template)

    _assert_saved(admin_client.post(
        reverse("admin:loans_collateral_change", args=[collateral.pk]),
        _collateral_body(loan.pk, "Honda Civic 2019"),
    ))

    contract.refresh_from_db()
    assert "Honda Civic 2019" in contract.content
    assert "Carro viejo" not in contract.content


# (c)
def test_collateral_delete_regenerates_the_pending_contract(admin_client, template, loan_factory):
    from apps.loans.models import Collateral

    loan = _pending(loan_factory)
    collateral = _collateral(loan, "Moto Yamaha")
    contract = _contract(loan, template)

    response = admin_client.post(
        reverse("admin:loans_collateral_delete", args=[collateral.pk]), {"post": "yes"}
    )
    assert response.status_code == 302
    assert not Collateral.objects.filter(pk=collateral.pk).exists()

    contract.refresh_from_db()
    assert "Sin garantías" in contract.content
    assert "Moto Yamaha" not in contract.content


# (d)
def test_collateral_bulk_delete_regenerates_every_affected_contract(admin_client, template, loan_factory):
    from apps.loans.models import Collateral

    first, second = _pending(loan_factory), _pending(loan_factory)
    c1, c2 = _collateral(first, "Moto Yamaha"), _collateral(second, "Camión Isuzu")
    k1, k2 = _contract(first, template), _contract(second, template)

    admin_client.post(reverse("admin:loans_collateral_changelist"), {
        "action": "delete_selected", "_selected_action": [c1.pk, c2.pk], "post": "yes",
    })
    assert not Collateral.objects.filter(pk__in=[c1.pk, c2.pk]).exists()

    for contract, description in ((k1, "Moto Yamaha"), (k2, "Camión Isuzu")):
        contract.refresh_from_db()
        assert "Sin garantías" in contract.content
        assert description not in contract.content


# (e)
def test_collateral_moved_to_another_loan_regenerates_both_contracts(admin_client, template, loan_factory):
    old_loan, new_loan = _pending(loan_factory), _pending(loan_factory)
    collateral = _collateral(old_loan, "Toyota Hilux")
    old_contract, new_contract = _contract(old_loan, template), _contract(new_loan, template)

    _assert_saved(admin_client.post(
        reverse("admin:loans_collateral_change", args=[collateral.pk]),
        _collateral_body(new_loan.pk, "Toyota Hilux"),
    ))

    old_contract.refresh_from_db()
    new_contract.refresh_from_db()
    assert "Toyota Hilux" not in old_contract.content
    assert "Sin garantías" in old_contract.content
    assert "Toyota Hilux" in new_contract.content


# (f)
def test_guarantor_add_change_and_delete_regenerate_the_pending_contract(
    admin_client, template, loan_factory
):
    from apps.loans.models_guarantors import Guarantor

    loan = _pending(loan_factory)
    contract = _contract(loan, template)

    _assert_saved(admin_client.post(reverse("admin:loans_guarantor_add"), _guarantor_body(loan.pk, "Ramón")))
    contract.refresh_from_db()
    assert "Ramón Gómez" in contract.content

    guarantor = Guarantor.objects.get(loan=loan)
    _assert_saved(admin_client.post(
        reverse("admin:loans_guarantor_change", args=[guarantor.pk]), _guarantor_body(loan.pk, "Julián")
    ))
    contract.refresh_from_db()
    assert "Julián Gómez" in contract.content
    assert "Ramón" not in contract.content

    response = admin_client.post(reverse("admin:loans_guarantor_delete", args=[guarantor.pk]), {"post": "yes"})
    assert response.status_code == 302
    assert not Guarantor.objects.filter(pk=guarantor.pk).exists()
    contract.refresh_from_db()
    assert "Garante: N/A" in contract.content
    assert "Julián" not in contract.content


def test_guarantor_moved_or_bulk_deleted_regenerates_every_affected_contract(
    admin_client, template, loan_factory
):
    from apps.loans.models_guarantors import Guarantor

    old_loan, new_loan = _pending(loan_factory), _pending(loan_factory)
    guarantor = _guarantor(old_loan, "Lucía")
    old_contract, new_contract = _contract(old_loan, template), _contract(new_loan, template)

    _assert_saved(admin_client.post(
        reverse("admin:loans_guarantor_change", args=[guarantor.pk]), _guarantor_body(new_loan.pk, "Lucía")
    ))
    old_contract.refresh_from_db()
    new_contract.refresh_from_db()
    assert "Garante: N/A" in old_contract.content
    assert "Lucía Gómez" in new_contract.content

    other = _guarantor(old_loan, "Marta")
    old_contract.content = "texto viejo"
    old_contract.save(update_fields=["content"])
    admin_client.post(reverse("admin:loans_guarantor_changelist"), {
        "action": "delete_selected", "_selected_action": [guarantor.pk, other.pk], "post": "yes",
    })
    assert not Guarantor.objects.filter(pk__in=[guarantor.pk, other.pk]).exists()
    old_contract.refresh_from_db()
    new_contract.refresh_from_db()
    assert "Garante: N/A" in old_contract.content
    assert "Garante: N/A" in new_contract.content


# (g)
def test_signed_contract_is_not_rewritten_by_the_collateral_admin(admin_client, template, loan_factory):
    loan = _pending(loan_factory)
    contract = _contract(loan, template, customer_signed_at=timezone.now())

    _assert_saved(admin_client.post(
        reverse("admin:loans_collateral_add"), _collateral_body(loan.pk, "Toyota Corolla 2020")
    ))

    contract.refresh_from_db()
    assert contract.content == "texto viejo"
