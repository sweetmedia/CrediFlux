"""Límite de usuarios del plan (`Tenant.max_users`) al crear miembros del equipo."""

import pytest


def _payload(n):
    return {
        "email": f"miembro{n}@crediflux.test",
        "username": f"miembro{n}",
        "first_name": "Luis",
        "last_name": "Martínez",
        "password": "clave-segura-123",
        "role": "loan_officer",
    }


@pytest.fixture
def set_max_users(tenant_schema):
    original = tenant_schema.max_users

    def _set(value):
        tenant_schema.max_users = value
        tenant_schema.save()

    yield _set
    tenant_schema.max_users = original  # la BD se revierte; el objeto de sesión no


def test_team_create_rejected_when_plan_limit_reached(auth_client, set_max_users):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    set_max_users(1)  # el dueño (auth_client) ya ocupa el único cupo
    before = User.objects.count()

    response = auth_client.post("/api/users/team/create/", _payload(1), format="json")

    assert response.status_code == 400, response.content
    assert "Límite de usuarios del plan alcanzado." in str(response.json())
    assert User.objects.count() == before
    assert not User.objects.filter(email="miembro1@crediflux.test").exists()


def test_team_create_allowed_below_plan_limit(auth_client, set_max_users):
    from django.contrib.auth import get_user_model

    set_max_users(2)

    response = auth_client.post("/api/users/team/create/", _payload(2), format="json")

    assert response.status_code == 201, response.content
    assert get_user_model().objects.filter(email="miembro2@crediflux.test").exists()


def test_inactive_users_do_not_count(auth_client, user_factory, set_max_users):
    user_factory(role="viewer", is_active=False)
    set_max_users(2)

    response = auth_client.post("/api/users/team/create/", _payload(3), format="json")

    assert response.status_code == 201, response.content


def test_reactivation_cannot_exceed_plan_limit(auth_client, user_factory, set_max_users):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    member_a = user_factory(role="viewer")
    set_max_users(2)  # dueño + A ocupan los dos cupos

    response = auth_client.patch(f"/api/users/team/{member_a.pk}/", {"is_active": False}, format="json")
    assert response.status_code == 200, response.content

    response = auth_client.post("/api/users/team/create/", _payload(4), format="json")
    assert response.status_code == 201, response.content

    response = auth_client.patch(f"/api/users/team/{member_a.pk}/", {"is_active": True}, format="json")
    assert response.status_code == 400, response.content
    assert "Límite de usuarios del plan alcanzado." in str(response.json())
    assert User.objects.get(pk=member_a.pk).is_active is False

    response = auth_client.put(
        f"/api/users/team/{member_a.pk}/",
        {"first_name": "A", "last_name": "B", "role": "viewer", "is_active": True},
        format="json",
    )
    assert response.status_code == 400, response.content
    assert User.objects.get(pk=member_a.pk).is_active is False
