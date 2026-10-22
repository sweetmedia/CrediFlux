"""Pruebas de humo de la infraestructura de tests.

Si alguna de éstas falla, el problema está en la configuración (settings,
conftest, base de datos) y no en el código de negocio.
"""

import pytest
from django.conf import settings
from django.db import connection


def test_usa_settings_de_test():
    assert settings.SETTINGS_MODULE == "config.settings.test"
    assert settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend"
    assert settings.CELERY_TASK_ALWAYS_EAGER is True


def test_tenant_schema_activo(tenant_schema):
    assert connection.schema_name == "test"
    assert tenant_schema.schema_name == "test"


def test_public_schema_activo(public_schema):
    assert connection.schema_name == "public"


def test_crea_usuario_del_tenant(user_factory):
    user = user_factory(role="loan_officer")
    assert user.pk is not None
    assert user.tenant.schema_name == "test"
    assert user.check_password("clave-de-prueba-123")


def test_los_datos_se_deshacen_entre_tests(tenant_schema):
    """El test anterior creó un usuario; la transacción lo deshizo."""
    from django.contrib.auth import get_user_model

    assert not get_user_model().objects.filter(role="loan_officer").exists()


@pytest.mark.parametrize("cliente", ["api_client", "public_client"])
def test_health_responde_en_ambos_schemas(cliente, request):
    client = request.getfixturevalue(cliente)
    response = client.get("/api/health/")
    assert response.status_code == 200, response.content


def test_auth_client_autenticado(auth_client):
    assert auth_client.user.role == "admin"
    assert auth_client.user.is_tenant_owner
