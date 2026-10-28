"""Catálogo de permisos y roles por financiera (D6, Task 7)."""
import pytest
from django.core.exceptions import ValidationError

from tests.authz_cases import CAMBIOS_PREVISTOS, CASE_NAMES, CODE, ROLES, permitido_hoy

SYSTEM_ROLE_KEYS = {
    'admin', 'manager', 'loan_officer', 'collector', 'collection_supervisor',
    'accountant', 'cashier', 'viewer',
}

# Los 47 códigos del prototipo aprobado (settings-roles.html) más los 3 añadidos.
CODIGOS_PROTOTIPO = {
    'customers.view', 'customers.create', 'customers.edit', 'customers.delete',
    'customers.documents.view', 'customers.documents.verify', 'customers.statement',
    'loans.view', 'loans.create', 'loans.edit', 'loans.approve', 'loans.reject',
    'loans.disburse', 'loans.calculator',
    'payments.view', 'payments.create', 'payments.void', 'payments.receipt',
    'collections.view', 'collections.reminders', 'collections.contacts', 'collections.mobile',
    'cashbox.view', 'cashbox.open', 'cashbox.close', 'cashbox.movements',
    'contracts.view', 'contracts.create', 'contracts.templates',
    'billing.view', 'billing.create', 'billing.sign', 'billing.submit', 'billing.reports',
    'comms.view', 'comms.email', 'comms.whatsapp', 'comms.tasks',
    'team.view', 'team.create', 'team.edit', 'team.delete', 'team.assign_roles',
    'settings.view', 'settings.edit', 'settings.audit',
    'ai.access',
}
CODIGOS_EXTRA = {'collections.supervise', 'cashbox.registers', 'billing.config'}


def _financiera(schema_name):
    """Financiera sin schema: los roles viven en public y no lo necesitan."""
    from apps.tenants.models import Tenant

    tenant = Tenant(schema_name=schema_name, name=schema_name, business_name=schema_name,
                    email=f'{schema_name}@financiera.test')
    tenant.auto_create_schema = False
    tenant.save()
    return tenant


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------


def test_catalogo_tiene_50_codigos_unicos():
    from apps.users.permissions_catalog import ALL_CODES, MODULES

    codigos = [codigo for _, _, items in MODULES for codigo, _ in items]
    assert len(codigos) == 50
    assert len(set(codigos)) == 50
    assert set(codigos) == ALL_CODES == CODIGOS_PROTOTIPO | CODIGOS_EXTRA
    assert len(CODIGOS_PROTOTIPO) == 47
    assert [clave for clave, _, _ in MODULES] == [
        'customers', 'loans', 'payments', 'collections', 'cashbox', 'contracts',
        'billing', 'comms', 'team', 'settings', 'ai',
    ]
    # Cada código pertenece al módulo cuya clave lleva de prefijo y tiene etiqueta.
    for clave, etiqueta, items in MODULES:
        assert etiqueta
        for codigo, nombre in items:
            assert codigo.split('.')[0] == clave and nombre


def test_defaults_cubren_los_8_roles_y_admin_tiene_todo():
    from apps.users.permissions_catalog import ALL_CODES, DEFAULT_ROLE_PERMISSIONS

    assert set(DEFAULT_ROLE_PERMISSIONS) == SYSTEM_ROLE_KEYS
    assert DEFAULT_ROLE_PERMISSIONS['admin'] == ALL_CODES
    for codigos in DEFAULT_ROLE_PERMISSIONS.values():
        assert codigos <= ALL_CODES
    assert {r for r, c in DEFAULT_ROLE_PERMISSIONS.items() if 'settings.audit' in c} == {'admin', 'manager'}


def test_code_de_la_matriz_usa_codigos_del_catalogo():
    from apps.users.permissions_catalog import ALL_CODES

    assert set(CODE) == set(CASE_NAMES)
    assert {c for c in CODE.values() if c is not None} <= ALL_CODES


def test_defaults_coinciden_con_la_matriz_de_hoy():
    """R7: para cada caso con código y cada rol, pasa hoy ⇔ el rol tiene el código.

    Las únicas discrepancias permitidas son las de CAMBIOS_PREVISTOS, y deben existir.
    """
    from apps.users.permissions_catalog import DEFAULT_ROLE_PERMISSIONS

    discrepancias = {}
    for case in CASE_NAMES:
        codigo = CODE[case]
        if codigo is None:
            continue
        for rol in ROLES:
            hoy = permitido_hoy(case, rol)
            despues = codigo in DEFAULT_ROLE_PERMISSIONS[rol]
            if hoy != despues:
                discrepancias[(case, rol)] = f'{codigo}: hoy={hoy} defaults={despues}'
    assert set(discrepancias) == set(CAMBIOS_PREVISTOS), discrepancias


def test_casos_sin_codigo_son_los_de_regla_propia():
    """`admin` = ALL_CODES: todo caso donde admin no pase hoy debe ser de regla propia."""
    assert {c for c, codigo in CODE.items() if codigo is None} == {'pago_revertir', 'usuario_asignar_admin'}
    for case in CASE_NAMES:
        if not permitido_hoy(case, 'admin'):
            assert CODE[case] is None, case


# ---------------------------------------------------------------------------
# Modelo Role y ensure_system_roles
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ensure_system_roles_crea_los_8_con_sus_defaults(public_schema):
    from apps.users.models import Role, ensure_system_roles
    from apps.users.permissions_catalog import DEFAULT_ROLE_PERMISSIONS

    financiera = _financiera('roles_a')
    Role.objects.filter(tenant=financiera).delete()  # sin la señal del alta
    ensure_system_roles(financiera)

    roles = {r.key: r for r in Role.objects.filter(tenant=financiera)}
    assert set(roles) == SYSTEM_ROLE_KEYS
    for key, rol in roles.items():
        assert rol.is_system
        assert rol.name
        assert set(rol.permissions) == DEFAULT_ROLE_PERMISSIONS[key]
    assert roles['collection_supervisor'].name == 'Supervisor de cobros'
    assert roles['viewer'].name == 'Solo lectura'


@pytest.mark.django_db
def test_ensure_system_roles_es_idempotente_y_no_pisa_un_rol_editado(public_schema):
    from apps.users.models import Role, ensure_system_roles

    financiera = _financiera('roles_b')
    ensure_system_roles(financiera)
    gerente = Role.objects.get(tenant=financiera, key='manager')
    gerente.name = 'Gerente general'
    gerente.permissions = ['loans.view']
    gerente.save()
    Role.objects.get(tenant=financiera, key='viewer').delete()

    ensure_system_roles(financiera)

    assert Role.objects.filter(tenant=financiera).count() == 8  # recrea el que falta
    gerente.refresh_from_db()
    assert gerente.name == 'Gerente general'
    assert gerente.permissions == ['loans.view']


@pytest.mark.django_db
def test_role_rechaza_codigos_fuera_del_catalogo(public_schema):
    from apps.users.models import Role

    financiera = _financiera('roles_c')
    rol = Role(tenant=financiera, key='raro', name='Raro', permissions=['x.y'])
    with pytest.raises(ValidationError) as exc:
        rol.full_clean()
    assert 'permissions' in exc.value.message_dict

    Role(tenant=financiera, key='bueno', name='Bueno', permissions=['loans.view']).full_clean()


@pytest.mark.django_db
def test_role_clean_quita_duplicados_y_ordena(public_schema):
    from apps.users.models import Role

    rol = Role(tenant=_financiera('roles_dup'), key='dup', name='Dup',
               permissions=['loans.view', 'customers.view', 'loans.view'])
    rol.full_clean()
    assert rol.permissions == ['customers.view', 'loans.view']


@pytest.mark.django_db
def test_clave_de_rol_cabe_en_user_role(public_schema):
    from apps.users.models import Role, User

    assert Role._meta.get_field('key').max_length == User._meta.get_field('role').max_length == 30
    rol = Role(tenant=_financiera('roles_len'), key='x' * 31, name='Larga')
    with pytest.raises(ValidationError) as exc:
        rol.full_clean()
    assert 'key' in exc.value.message_dict


@pytest.mark.django_db
def test_mismo_rol_en_dos_financieras_son_filas_distintas(public_schema):
    from apps.users.models import Role

    norte_a = Role.objects.create(tenant=_financiera('roles_d'), key='cobrador-norte',
                                  name='Cobrador norte', permissions=['collections.view'])
    norte_b = Role.objects.create(tenant=_financiera('roles_e'), key='cobrador-norte',
                                  name='Cobrador norte', permissions=['collections.view'])
    assert norte_a.pk != norte_b.pk

    norte_a.permissions = ['collections.view', 'collections.mobile']
    norte_a.save()
    norte_b.refresh_from_db()
    assert norte_b.permissions == ['collections.view']


@pytest.mark.django_db
def test_clave_unica_por_financiera(public_schema):
    from django.db import IntegrityError, transaction

    from apps.users.models import Role

    financiera = _financiera('roles_f')
    Role.objects.create(tenant=financiera, key='caja-2', name='Caja 2')
    with pytest.raises(IntegrityError), transaction.atomic():
        Role.objects.create(tenant=financiera, key='caja-2', name='Otra')


# ---------------------------------------------------------------------------
# Dónde se crean: cualquier alta (señal), registro, admin, aprovisionamiento,
# init_public_tenant, migración de datos
# ---------------------------------------------------------------------------


def _claves(tenant):
    from apps.users.models import Role

    return set(Role.objects.filter(tenant=tenant).values_list('key', flat=True))


@pytest.mark.django_db
def test_crear_un_tenant_directamente_crea_sus_roles(public_schema, monkeypatch):
    from apps.tenants.models import Tenant

    monkeypatch.setattr(Tenant, 'auto_create_schema', False)  # sin CREATE SCHEMA en el test

    financiera = Tenant(schema_name='roles_directo', name='d', business_name='d', email='d@f.test')
    financiera.save()
    assert _claves(financiera) == SYSTEM_ROLE_KEYS

    otra = Tenant.objects.create(schema_name='roles_create', name='c', business_name='c', email='c@f.test',
                                 provisioning_pending=True, is_active=False)
    assert _claves(otra) == SYSTEM_ROLE_KEYS


@pytest.mark.django_db
def test_crear_un_tenant_desde_el_admin_crea_sus_roles(public_schema):
    from django.contrib import admin
    from django.test import RequestFactory

    from apps.tenants.models import Tenant

    financiera = Tenant(schema_name='roles_admin', name='a', business_name='a', email='a@f.test',
                        provisioning_pending=True, is_active=False)  # save_model no le crea schema
    request = RequestFactory().post('/admin/tenants/tenant/add/')
    admin.site._registry[Tenant].save_model(request, financiera, form=None, change=False)
    assert _claves(financiera) == SYSTEM_ROLE_KEYS


@pytest.mark.django_db
def test_guardar_un_tenant_existente_no_recrea_roles_borrados(public_schema):
    from apps.users.models import Role

    financiera = _financiera('roles_resave')
    Role.objects.filter(tenant=financiera, key='viewer').delete()
    financiera.name = 'otro nombre'
    financiera.save()
    assert 'viewer' not in _claves(financiera)  # la señal sólo actúa en el alta


@pytest.mark.django_db
def test_init_public_tenant_deja_los_roles_del_tenant_publico(public_schema):
    from django.core.management import call_command

    from apps.tenants.models import Tenant
    from apps.users.models import Role

    publico = Tenant.objects.get(schema_name='public')
    Role.objects.filter(tenant=publico).delete()  # como un public creado antes de D6
    call_command('init_public_tenant', '--domain', 'localhost', stdout=__import__('io').StringIO())
    assert _claves(publico) == SYSTEM_ROLE_KEYS


@pytest.mark.django_db
def test_el_registro_crea_los_roles_de_la_financiera(public_client, monkeypatch):
    from django.core.cache import cache

    from apps.tenants.models import Tenant
    from apps.tenants.tests.test_security_registration import URL, payload
    from apps.users.models import Role

    cache.clear()
    monkeypatch.setattr(Tenant, 'auto_create_schema', False)
    response = public_client.post(URL, payload(), format='json', REMOTE_ADDR='198.51.100.77')
    cache.clear()

    assert response.status_code in (201, 202), response.content
    financiera = Tenant.objects.get(name='financiera-nueva')
    assert set(Role.objects.filter(tenant=financiera).values_list('key', flat=True)) == SYSTEM_ROLE_KEYS


@pytest.mark.django_db
def test_aprovisionar_un_pendiente_asegura_sus_roles(public_schema, monkeypatch):
    from apps.tenants.models import Tenant
    from apps.tenants.provisioning import provision_pending_tenant
    from apps.users.models import Role

    financiera = _financiera('roles_pend')
    Tenant.objects.filter(pk=financiera.pk).update(provisioning_pending=True, is_active=False)
    Role.objects.filter(tenant=financiera).delete()  # pendiente registrado antes de D6
    monkeypatch.setattr(Tenant, 'create_schema', lambda self, *a, **kw: None)

    assert provision_pending_tenant(financiera.pk) is True
    assert set(Role.objects.filter(tenant=financiera).values_list('key', flat=True)) == SYSTEM_ROLE_KEYS


@pytest.mark.django_db
def test_ensure_system_roles_dos_veces_sobre_el_tenant_de_pruebas(tenant_schema):
    """Con el search_path en un schema de tenant los roles siguen en public y no se duplican."""
    from apps.users.models import Role, ensure_system_roles

    ensure_system_roles(tenant_schema)
    ensure_system_roles(tenant_schema)
    assert set(Role.objects.filter(tenant=tenant_schema).values_list('key', flat=True)) == SYSTEM_ROLE_KEYS


@pytest.mark.django_db
def test_la_funcion_de_la_migracion_crea_los_roles_de_cada_tenant(public_schema):
    """La función de la migración, con los modelos vivos, cubre a todos los tenants."""
    from django.apps import apps as django_apps

    from apps.users.models import Role
    from apps.users.models_roles import crear_roles_de_sistema_para_todos

    financiera = _financiera('roles_mig')
    Role.objects.filter(tenant=financiera).delete()  # tenant anterior a D6
    crear_roles_de_sistema_para_todos(django_apps.get_model('tenants', 'Tenant'), Role)
    assert set(Role.objects.filter(tenant=financiera).values_list('key', flat=True)) == SYSTEM_ROLE_KEYS
