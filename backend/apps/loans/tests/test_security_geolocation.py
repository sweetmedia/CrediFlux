"""Visitas y ubicaciones de cobradores acotadas al propio cobrador.

Un cobrador sólo ve y edita lo suyo; gerencia y supervisión de cobranza ven todo.
Crear visitas exige un rol de cobranza y el `collector` siempre es quien la crea.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

TENANT_HOST = "tenant.test.localhost"
VISITS = "/api/loans/collector-visits/"
LOCATIONS = "/api/loans/collector-locations/"


def _client_for(user):
    client = APIClient(HTTP_HOST=TENANT_HOST)
    client.force_authenticate(user=user)
    return client


def _rows(response):
    data = response.json()
    return data.get("results", data) if isinstance(data, dict) else data


@pytest.fixture
def collector_a(user_factory):
    return user_factory(role="collector")


@pytest.fixture
def collector_b(user_factory):
    return user_factory(role="collector")


@pytest.fixture
def visit_a(collector_a, customer_factory):
    from apps.loans.models_geolocation import CollectorVisit

    return CollectorVisit.objects.create(
        collector=collector_a,
        customer=customer_factory(),
        latitude=Decimal("18.4861000"),
        longitude=Decimal("-69.9312000"),
        notes="original",
    )


@pytest.fixture
def location_a(collector_a, tenant_schema):
    from apps.loans.models_geolocation import CollectorLocation

    return CollectorLocation.objects.create(
        collector=collector_a,
        latitude=Decimal("18.4861000"),
        longitude=Decimal("-69.9312000"),
    )


def _visit_payload(customer):
    return {
        "customer": str(customer.id),
        "latitude": "18.4861000",
        "longitude": "-69.9312000",
        "visit_type": "collection",
    }


def test_collector_cannot_see_or_edit_another_collectors_visit(collector_b, visit_a):
    client = _client_for(collector_b)

    assert client.get(f"{VISITS}{visit_a.id}/").status_code == 404
    response = client.patch(f"{VISITS}{visit_a.id}/", {"notes": "hackeado"}, format="json")
    assert response.status_code == 404

    visit_a.refresh_from_db()
    assert visit_a.notes == "original"

    listing = client.get(VISITS)
    assert listing.status_code == 200
    assert str(visit_a.id) not in {row["id"] for row in _rows(listing)}


def test_collector_cannot_checkout_another_collectors_visit(collector_b, visit_a):
    response = _client_for(collector_b).post(f"{VISITS}{visit_a.id}/checkout/", {}, format="json")
    assert response.status_code == 404
    visit_a.refresh_from_db()
    assert visit_a.checked_out_at is None


def test_supervisor_sees_any_collectors_visit(user_factory, visit_a):
    client = _client_for(user_factory(role="collection_supervisor"))
    response = client.get(f"{VISITS}{visit_a.id}/")
    assert response.status_code == 200
    assert response.json()["id"] == str(visit_a.id)


def test_viewer_cannot_create_visit(user_factory, customer_factory):
    from apps.loans.models_geolocation import CollectorVisit

    response = _client_for(user_factory(role="viewer")).post(
        VISITS, _visit_payload(customer_factory()), format="json"
    )
    assert response.status_code == 403
    assert CollectorVisit.objects.count() == 0


def test_collector_creates_own_visit_even_if_other_collector_is_sent(
    collector_a, collector_b, customer_factory
):
    from apps.loans.models_geolocation import CollectorVisit

    payload = _visit_payload(customer_factory())
    payload["collector"] = str(collector_a.id)

    response = _client_for(collector_b).post(VISITS, payload, format="json")

    assert response.status_code == 201
    visit = CollectorVisit.objects.get()
    assert visit.collector_id == collector_b.id


def test_collector_cannot_see_another_collectors_locations(collector_a, collector_b, location_a):
    client = _client_for(collector_b)

    assert client.get(f"{LOCATIONS}{location_a.id}/").status_code == 404

    route = client.get(LOCATIONS + "route/", {"collector": str(collector_a.id)})
    assert route.status_code == 200
    assert route.json() == []

    latest = client.get(LOCATIONS + "latest/")
    assert latest.status_code == 200
    assert str(location_a.id) not in {row["id"] for row in latest.json()}


def test_supervisor_sees_any_collectors_location(user_factory, collector_a, location_a):
    client = _client_for(user_factory(role="collection_supervisor"))
    assert client.get(f"{LOCATIONS}{location_a.id}/").status_code == 200
    route = client.get(LOCATIONS + "route/", {"collector": str(collector_a.id)})
    assert [row["id"] for row in route.json()] == [str(location_a.id)]
