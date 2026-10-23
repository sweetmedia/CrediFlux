"""
Configuración raíz de pytest para el backend de CrediFlux.

Multi-tenancy: CrediFlux usa django-tenants (un schema de Postgres por
tenant), así que la suite necesita Postgres de verdad. pytest-django crea
`test_<DB_NAME>` y corre `migrate` (que django-tenants convierte en
`migrate_schemas`) para el schema `public`. Encima de eso, este conftest crea
UNA VEZ por sesión:

* el tenant público (schema `public`, dominio `localhost`), y
* un tenant de pruebas (schema `test`, dominio `tenant.test.localhost`) con
  sus migraciones de TENANT_APPS aplicadas.

Cada test que use `tenant_schema` corre dentro de la transacción de
pytest-django con el `search_path` apuntando al schema del tenant, así que
todo lo que cree se deshace al terminar. `--reuse-db` (en pyproject) conserva
la base y el schema entre corridas; usa `--create-db` si cambias migraciones.

Las fixtures compartidas viven aquí (un `pytest_plugins` sólo vale en el
conftest raíz). Las fábricas de modelos están en `tests/factories.py`.
"""

import pytest
from django.db import connection

TEST_TENANT_SCHEMA = "test"
TEST_TENANT_DOMAIN = "tenant.test.localhost"
PUBLIC_DOMAIN = "localhost"


# ---------------------------------------------------------------------------
# Tenants (scope de sesión: crear un schema corre todas las migraciones)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def public_tenant(django_db_setup, django_db_blocker):
    """Tenant del schema `public` con su dominio `localhost`."""
    from apps.tenants.models import Domain, Tenant

    with django_db_blocker.unblock():
        tenant, _ = Tenant.objects.get_or_create(
            schema_name="public",
            defaults={
                "name": "CrediFlux (public)",
                "business_name": "CrediFlux",
                "email": "public@crediflux.test",
            },
        )
        Domain.objects.get_or_create(
            domain=PUBLIC_DOMAIN, defaults={"tenant": tenant, "is_primary": True}
        )
    return tenant


@pytest.fixture(scope="session")
def tenant(public_tenant, django_db_blocker):
    """Tenant de pruebas con schema propio (`test`) ya migrado."""
    from apps.tenants.models import Domain, Tenant

    with django_db_blocker.unblock():
        connection.set_schema_to_public()
        tenant = Tenant.objects.filter(schema_name=TEST_TENANT_SCHEMA).first()
        if tenant is None:
            tenant = Tenant(
                schema_name=TEST_TENANT_SCHEMA,
                name="Financiera de Prueba",
                business_name="Financiera de Prueba SRL",
                email="admin@financiera.test",
            )
            tenant.save(verbosity=0)  # crea el schema y migra TENANT_APPS
        Domain.objects.get_or_create(
            domain=TEST_TENANT_DOMAIN, defaults={"tenant": tenant, "is_primary": True}
        )
    return tenant


OTHER_TENANT_DOMAIN = "other.test.localhost"


@pytest.fixture
def other_tenant(db, public_schema):
    """Segundo tenant SIN schema propio (`auto_create_schema = False`).

    Sólo sirve para que `other.test.localhost` resuelva a un tenant distinto
    y probar que una credencial del tenant de pruebas no vale en otro host.
    """
    from apps.tenants.models import Domain, Tenant

    tenant = Tenant(
        schema_name="other",
        name="Otra Financiera",
        business_name="Otra Financiera SRL",
        email="admin@otra.test",
    )
    tenant.auto_create_schema = False
    tenant.save(verbosity=0)
    Domain.objects.create(domain=OTHER_TENANT_DOMAIN, tenant=tenant, is_primary=True)
    return tenant


@pytest.fixture
def tenant_schema(db, tenant):
    """Activa el schema del tenant de pruebas durante el test."""
    connection.set_tenant(tenant)
    yield tenant
    connection.set_schema_to_public()


@pytest.fixture
def public_schema(db, public_tenant):
    """Fuerza el schema `public` durante el test (rutas de urls_public)."""
    connection.set_schema_to_public()
    yield public_tenant
    connection.set_schema_to_public()


# ---------------------------------------------------------------------------
# Usuarios y clientes HTTP
# ---------------------------------------------------------------------------


@pytest.fixture
def user_factory(tenant_schema):
    """Fábrica de usuarios ligados al tenant de pruebas.

    `user_factory(role="loan_officer", email="x@y.z")` — los kwargs van al
    UserFactory de `tests/factories.py`.
    """
    from tests.factories import UserFactory

    def _create(**overrides):
        overrides.setdefault("tenant", tenant_schema)
        return UserFactory(**overrides)

    return _create


@pytest.fixture
def admin_user(user_factory):
    """Usuario administrador (dueño) del tenant de pruebas."""
    return user_factory(role="admin", is_tenant_owner=True)


@pytest.fixture
def api_client(tenant_schema):
    """APIClient de DRF apuntando al dominio del tenant de pruebas.

    TenantMainMiddleware resuelve el tenant por el Host, así que cada request
    sale con `HTTP_HOST=tenant.test.localhost`.
    """
    from rest_framework.test import APIClient

    return APIClient(HTTP_HOST=TEST_TENANT_DOMAIN)


@pytest.fixture
def auth_client(api_client, admin_user):
    """APIClient del tenant autenticado como `admin_user`."""
    api_client.force_authenticate(user=admin_user)
    api_client.user = admin_user
    return api_client


@pytest.fixture
def public_client(public_schema):
    """APIClient de DRF apuntando al schema público (`localhost`)."""
    from rest_framework.test import APIClient

    return APIClient(HTTP_HOST=PUBLIC_DOMAIN)
