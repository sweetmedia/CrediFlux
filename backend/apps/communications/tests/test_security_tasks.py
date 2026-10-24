"""Tablero de tareas: escribir exige un rol operativo (run-2)."""
import pytest
from rest_framework.test import APIClient

from apps.communications.models import Task
from apps.users.tokens import issue_tokens

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"
BASE = "/api/communications/tasks/"
READ_ONLY_ROLES = ["viewer", "cashier", "accountant"]


def _client(user):
    client = APIClient(HTTP_HOST=HOST)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user).access_token}")
    return client


@pytest.fixture
def owner_task(user_factory):
    admin = user_factory(role="admin")
    return Task.objects.create(title="Seguimiento de cobro", status="todo", position=0, created_by=admin)


@pytest.mark.parametrize("role", READ_ONLY_ROLES)
def test_read_only_roles_cannot_write_tasks(role, user_factory, owner_task):
    client = _client(user_factory(role=role))

    assert client.get(BASE).status_code == 200
    assert client.post(BASE, {"title": "nueva"}, format="json").status_code == 403
    assert client.patch(f"{BASE}{owner_task.pk}/", {"title": "editada"}, format="json").status_code == 403
    assert client.post(f"{BASE}{owner_task.pk}/move/", {"status": "done"}, format="json").status_code == 403
    assert client.post(
        f"{BASE}reorder/", {"tasks": [{"id": str(owner_task.pk), "position": 9}]}, format="json"
    ).status_code == 403
    assert client.delete(f"{BASE}{owner_task.pk}/").status_code == 403

    owner_task.refresh_from_db()
    assert (owner_task.title, owner_task.status, owner_task.position) == ("Seguimiento de cobro", "todo", 0)
    assert Task.objects.count() == 1


@pytest.mark.parametrize("overrides", [{"role": "collector"}, {"role": "viewer", "is_tenant_owner": True}])
def test_operational_roles_and_owner_can_write_tasks(overrides, user_factory, owner_task):
    client = _client(user_factory(**overrides))

    assert client.post(BASE, {"title": "nueva"}, format="json").status_code == 201
    assert client.patch(f"{BASE}{owner_task.pk}/", {"title": "editada"}, format="json").status_code == 200
    assert client.post(f"{BASE}{owner_task.pk}/move/", {"status": "done"}, format="json").status_code == 200
    assert client.delete(f"{BASE}{owner_task.pk}/").status_code == 204
