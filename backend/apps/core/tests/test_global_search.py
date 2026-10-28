"""Búsqueda global sobre el catálogo (D6): cada sección sólo con el código que deja ver ese dato."""
from datetime import date
from decimal import Decimal

import pytest
from moneyed import Money

from apps.core import views
from tests.authz_helpers import cambiar_rol, comprobar_completitud_apiview

pytestmark = pytest.mark.django_db

URL = '/api/search/'
SECCIONES = ('customers', 'loans', 'payments', 'contracts')
CODIGO_DE = {
    'customers': 'customers.view',
    'loans': 'loans.view',
    'payments': 'payments.view',
    'contracts': 'contracts.view',
}


def test_la_vista_declara_su_mapa():
    comprobar_completitud_apiview(views.GlobalSearchView)


@pytest.fixture
def datos(tenant_schema):
    """Un cliente «Zoila Buscable» con préstamo, pago y contrato que la búsqueda encuentra."""
    from apps.loans.models import Customer, Loan, LoanPayment
    from apps.loans.models_contracts import Contract

    cliente = Customer.objects.create(
        first_name='Zoila', last_name='Buscable', date_of_birth=date(1980, 1, 1), gender='F',
        email='zoila@crediflux.test', phone='+18095550099', address_line1='Calle 9',
        city='Santo Domingo', state='DN', postal_code='10101', id_type='cedula',
        id_number='001-1111111-1', employment_status='employed',
    )
    prestamo = Loan.objects.create(
        customer=cliente, loan_type='personal', principal_amount=Money(Decimal('5000.00'), 'DOP'),
        interest_rate=Decimal('5.00'), interest_type='french', term_months=6,
        payment_frequency='monthly', payment_amount=Money(Decimal('1.00'), 'DOP'), status='active',
        disbursement_date=date(2026, 1, 1), first_payment_date=date(2026, 2, 1),
    )
    LoanPayment.objects.create(
        loan=prestamo, amount=Money(Decimal('500.00'), 'DOP'), payment_method='cash',
        status='completed',
    )
    Contract.objects.create(loan=prestamo, content='Contrato de búsqueda')
    return cliente


def _buscar(api_client, user):
    api_client.force_authenticate(user=user)
    resp = api_client.get(URL, {'q': 'Buscable'})
    assert resp.status_code == 200, resp.content
    return resp.json()


def test_con_los_cuatro_codigos_ve_las_cuatro_secciones(api_client, user_factory, datos):
    body = _buscar(api_client, user_factory(role='viewer'))
    for seccion in SECCIONES:
        assert len(body['results'][seccion]) == 1, seccion
    assert body['total_results'] == 4


def test_rol_solo_de_caja_no_ve_ninguna_seccion(api_client, user_factory, tenant_schema, datos):
    """Rol propio con sólo cashbox.*: la búsqueda responde, pero vacía."""
    from apps.users.models import Role

    Role.objects.create(
        tenant=tenant_schema, key='solo-caja', name='Sólo caja',
        permissions=['cashbox.view', 'cashbox.open', 'cashbox.close', 'cashbox.movements'],
    )
    body = _buscar(api_client, user_factory(role='solo-caja'))
    assert body['results'] == {seccion: [] for seccion in SECCIONES}
    assert body['total_results'] == 0


@pytest.mark.parametrize('seccion', SECCIONES)
def test_cada_seccion_depende_de_su_codigo(api_client, user_factory, tenant_schema, datos, seccion):
    cambiar_rol(tenant_schema, 'viewer', quitar=[CODIGO_DE[seccion]])
    body = _buscar(api_client, user_factory(role='viewer'))
    assert body['results'][seccion] == []
    for otra in set(SECCIONES) - {seccion}:
        assert len(body['results'][otra]) == 1, otra
