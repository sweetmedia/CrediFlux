"""D4: apodo y supervisor inmediato del cliente."""

import pytest


@pytest.mark.django_db
def test_patch_guarda_apodo_y_supervisor(auth_client, customer_factory):
    cliente = customer_factory()
    resp = auth_client.patch(
        f"/api/loans/customers/{cliente.id}/",
        {
            "nickname": "La Flaca",
            "supervisor_name": "Ramón Peña",
            "supervisor_phone": "+18095551234",
        },
        format="json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["nickname"] == "La Flaca"
    assert data["supervisor_name"] == "Ramón Peña"
    assert data["supervisor_phone"] == "+18095551234"
    cliente.refresh_from_db()
    assert cliente.nickname == "La Flaca"
    assert cliente.supervisor_name == "Ramón Peña"
    assert str(cliente.supervisor_phone) == "+18095551234"


@pytest.mark.django_db
def test_supervisor_phone_invalido_da_400(auth_client, customer_factory):
    cliente = customer_factory()
    resp = auth_client.patch(
        f"/api/loans/customers/{cliente.id}/",
        {"supervisor_phone": "123"},
        format="json",
    )
    assert resp.status_code == 400
    assert "supervisor_phone" in resp.json()


@pytest.mark.django_db
def test_busqueda_por_apodo_y_listado_lo_incluye(auth_client, customer_factory):
    cliente = customer_factory(nickname="La Flaca")
    customer_factory()
    resp = auth_client.get("/api/loans/customers/?search=flaca")
    assert resp.status_code == 200
    body = resp.json()
    results = body["results"] if isinstance(body, dict) else body
    assert [r["id"] for r in results] == [str(cliente.id)]
    assert results[0]["nickname"] == "La Flaca"
