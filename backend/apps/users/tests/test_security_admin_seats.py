"""Cupo de usuarios del plan (Tenant.max_users) también en el admin de Django (run-2).

Cubre: la acción "activar usuarios", el formulario de alta y la casilla is_active del
formulario de edición respetan el cupo; con cupo libre siguen funcionando; el
superusuario de plataforma no está limitado.
"""
import pytest
from django.test import Client
from django.urls import reverse

from apps.users.models import User

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"


@pytest.fixture
def one_seat_tenant(tenant_schema):
    original = tenant_schema.max_users
    tenant_schema.max_users = 1
    tenant_schema.save(update_fields=["max_users"])
    yield tenant_schema
    tenant_schema.max_users = original
    tenant_schema.save(update_fields=["max_users"])


@pytest.fixture
def owner_client(one_seat_tenant, user_factory):
    owner = user_factory(role="admin", is_tenant_owner=True, is_staff=True)
    client = Client(HTTP_HOST=HOST)
    client.force_login(owner)
    return client


def _active_count(tenant):
    return User.objects.filter(tenant=tenant, is_active=True).count()


def _add_body(email="nuevo-asiento@crediflux.test"):
    return {
        "email": email, "username": email.split("@")[0], "first_name": "N", "last_name": "U",
        "role": "viewer", "password1": "Nueva-Clave-456!", "password2": "Nueva-Clave-456!",
    }


def test_activate_action_respects_the_seat_cap(owner_client, one_seat_tenant, user_factory):
    inactive = [user_factory(is_active=False), user_factory(is_active=False)]
    owner_client.post(
        reverse("admin:users_user_changelist"),
        {"action": "activate_users", "_selected_action": [u.pk for u in inactive]},
    )
    assert _active_count(one_seat_tenant) == 1


def test_add_form_respects_the_seat_cap(owner_client, one_seat_tenant):
    response = owner_client.post(reverse("admin:users_user_add"), _add_body())
    assert response.status_code == 403
    assert not User.objects.filter(email="nuevo-asiento@crediflux.test").exists()
    assert _active_count(one_seat_tenant) == 1


def test_change_form_reactivation_respects_the_seat_cap(owner_client, one_seat_tenant, user_factory):
    member = user_factory(role="viewer", is_active=False)
    body = {
        "username": member.username, "email": member.email, "first_name": member.first_name,
        "last_name": member.last_name, "role": member.role, "is_active": "on",
    }
    response = owner_client.post(reverse("admin:users_user_change", args=[member.pk]), body)
    assert response.status_code == 403
    member.refresh_from_db()
    assert member.is_active is False


def test_free_seats_still_allow_activation(owner_client, one_seat_tenant, user_factory):
    one_seat_tenant.max_users = 3
    one_seat_tenant.save(update_fields=["max_users"])
    inactive = user_factory(is_active=False)
    owner_client.post(
        reverse("admin:users_user_changelist"), {"action": "activate_users", "_selected_action": [inactive.pk]}
    )
    inactive.refresh_from_db()
    assert inactive.is_active
    assert owner_client.post(reverse("admin:users_user_add"), _add_body()).status_code == 302
    assert _active_count(one_seat_tenant) == 3


def test_platform_superuser_is_not_capped(one_seat_tenant, user_factory):
    client = Client(HTTP_HOST=HOST)
    client.force_login(user_factory(tenant=None, is_superuser=True, is_staff=True))
    inactive = user_factory(is_active=False)
    client.post(reverse("admin:users_user_changelist"), {"action": "activate_users", "_selected_action": [inactive.pk]})
    inactive.refresh_from_db()
    assert inactive.is_active
