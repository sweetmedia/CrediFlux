"""D4: «garante de otros clientes», calculado por cédula del garante."""

import pytest

from apps.loans.models_guarantors import Guarantor


def _garante(loan, id_number="001-2345111-0", **kw):
    data = dict(
        loan=loan, first_name="Pedro", last_name="Garante", id_type="cedula",
        id_number=id_number, phone="+18095550001", address="Calle 2",
        relationship="friend",
    )
    data.update(kw)
    return Guarantor.objects.create(**data)


@pytest.fixture
def escenario(customer_factory, loan_factory):
    juan = customer_factory(first_name="Juan", last_name="Díaz")
    carmen = customer_factory(first_name="Carmen", last_name="Lora", id_number="00123451110")
    prestamo_juan = loan_factory(customer=juan)
    return juan, carmen, prestamo_juan


def test_save_rellena_id_number_digits(escenario):
    _, _, prestamo = escenario
    g = _garante(prestamo, id_number="001-2345111-0")
    g.refresh_from_db()
    assert g.id_number_digits == "00123451110"


@pytest.mark.django_db
def test_detalle_trae_guarantor_of(auth_client, escenario):
    juan, carmen, prestamo = escenario
    _garante(prestamo)
    resp = auth_client.get(f"/api/loans/customers/{carmen.id}/")
    assert resp.status_code == 200, resp.content
    lista = resp.json()["guarantor_of"]
    assert len(lista) == 1
    assert lista[0]["loan_number"] == prestamo.loan_number
    assert lista[0]["loan_id"] == str(prestamo.id)
    assert lista[0]["customer_id"] == str(juan.id)
    assert lista[0]["customer_name"].startswith("Juan")
    assert lista[0]["status"] == prestamo.status


@pytest.mark.django_db
def test_garante_liberado_no_aparece(auth_client, escenario):
    _, carmen, prestamo = escenario
    _garante(prestamo, status="released")
    assert auth_client.get(f"/api/loans/customers/{carmen.id}/").json()["guarantor_of"] == []


@pytest.mark.django_db
def test_garante_en_prestamo_propio_no_aparece(auth_client, escenario, loan_factory):
    _, carmen, _ = escenario
    propio = loan_factory(customer=carmen)
    _garante(propio)
    assert auth_client.get(f"/api/loans/customers/{carmen.id}/").json()["guarantor_of"] == []


@pytest.mark.django_db
def test_guarantor_check_cliente_existente(auth_client, escenario):
    juan, carmen, prestamo = escenario
    _garante(prestamo)
    resp = auth_client.get("/api/loans/customers/guarantor-check/", {"id_number": "001-2345111-0"})
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["is_customer"] is True
    assert body["customer_id"] == str(carmen.id)
    assert [g["loan_number"] for g in body["guarantor_of"]] == [prestamo.loan_number]


@pytest.mark.django_db
def test_guarantor_check_desconocida(auth_client, escenario):
    resp = auth_client.get("/api/loans/customers/guarantor-check/", {"id_number": "999-9999999-9"})
    assert resp.status_code == 200
    assert resp.json() == {"is_customer": False, "customer_id": None, "guarantor_of": []}


@pytest.mark.django_db
def test_guarantor_check_vacio_da_400(auth_client):
    resp = auth_client.get("/api/loans/customers/guarantor-check/", {"id_number": ""})
    assert resp.status_code == 400


# --- Ola final F2: garante en mora, préstamos cerrados y datos del préstamo con loans.view ---

@pytest.mark.django_db
def test_garante_en_mora_aparece(auth_client, escenario):
    _, carmen, prestamo = escenario
    _garante(prestamo, status="defaulted")
    lista = auth_client.get(f"/api/loans/customers/{carmen.id}/").json()["guarantor_of"]
    assert [g["loan_number"] for g in lista] == [prestamo.loan_number]


@pytest.mark.django_db
@pytest.mark.parametrize("estado", ["paid", "rejected"])
def test_prestamo_cerrado_no_cuenta(auth_client, escenario, estado):
    _, carmen, prestamo = escenario
    prestamo.status = estado
    prestamo.save()
    _garante(prestamo)
    assert auth_client.get(f"/api/loans/customers/{carmen.id}/").json()["guarantor_of"] == []


@pytest.mark.django_db
def test_sin_loans_view_no_trae_numero_ni_estado_del_prestamo(
    api_client, user_factory, tenant_schema, escenario
):
    from tests.authz_helpers import cambiar_rol

    juan, carmen, prestamo = escenario
    _garante(prestamo)
    cambiar_rol(tenant_schema, "viewer", quitar=["loans.view"])
    api_client.force_authenticate(user=user_factory(role="viewer"))
    detalle = api_client.get(f"/api/loans/customers/{carmen.id}/").json()["guarantor_of"]
    check = api_client.get(
        "/api/loans/customers/guarantor-check/", {"id_number": "001-2345111-0"}
    ).json()["guarantor_of"]
    for lista in (detalle, check):
        assert lista == [{"customer_id": str(juan.id), "customer_name": juan.get_full_name()}]


@pytest.mark.django_db
def test_guarantor_check_con_cedula_repetida_elige_el_cliente_mas_antiguo(
    auth_client, customer_factory, escenario
):
    _, carmen, _ = escenario
    # Misma cédula con otro formato (la columna es única por texto, no por dígitos).
    customer_factory(first_name="Carmen", last_name="Duplicada", id_number="001-2345111-0")
    body = auth_client.get(
        "/api/loans/customers/guarantor-check/", {"id_number": "00123451110"}
    ).json()
    assert body["customer_id"] == str(carmen.id)
