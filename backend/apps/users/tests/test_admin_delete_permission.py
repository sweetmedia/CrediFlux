"""Run-8 L5: en el admin de Django, borrar un usuario exige team.delete (como la API), no
sólo team.edit."""
import pytest
from django.test import Client
from django.urls import reverse

from apps.users.permissions_catalog import DEFAULT_ROLE_PERMISSIONS

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"


def _cliente_con_rol(user_factory, tenant, codigos):
    from apps.users.models import Role

    key = f"equipo-{len(codigos)}"
    Role.objects.create(
        tenant=tenant, key=key, name="Equipo",
        permissions=sorted(DEFAULT_ROLE_PERMISSIONS["viewer"] | set(codigos)),
    )
    client = Client(HTTP_HOST=HOST)
    client.force_login(user_factory(role=key, is_staff=True))
    return client


def test_team_edit_sin_team_delete_no_borra(user_factory, tenant_schema):
    destino = user_factory(role="viewer")
    client = _cliente_con_rol(user_factory, tenant_schema, ["team.edit"])
    url = reverse("admin:users_user_delete", args=[destino.pk])
    assert client.get(url).status_code == 403
    assert client.post(url, {"post": "yes"}).status_code == 403
    destino.refresh_from_db()  # sigue existiendo


def test_team_delete_si_borra(user_factory, tenant_schema):
    destino = user_factory(role="viewer")
    client = _cliente_con_rol(user_factory, tenant_schema, ["team.edit", "team.delete"])
    assert client.get(reverse("admin:users_user_delete", args=[destino.pk])).status_code == 200
