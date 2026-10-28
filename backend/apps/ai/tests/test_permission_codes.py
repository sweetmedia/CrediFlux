"""Asistente IA sobre el catálogo (D6): `ai.access` para usarlo y, dentro de cada herramienta,
el código del dato que lee (customers.view, loans.view, payments.view)."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

import pytest
from django.test import override_settings
from moneyed import Money

from apps.ai import tools, views
from apps.ai.tools import con_usuario
from tests.authz_helpers import cambiar_rol, comprobar_completitud_apiview

pytestmark = pytest.mark.django_db

CHAT_URL = '/api/ai/chat/'
AGENTS_URL = '/api/ai/agents/'


@pytest.mark.parametrize('cls', [views.ChatView, views.AgentsListView, views.AIConfigView],
                         ids=lambda c: c.__name__)
def test_cada_metodo_de_cada_vista_tiene_su_codigo(cls):
    comprobar_completitud_apiview(cls)


def test_rol_sin_ai_access_recibe_403_en_chat_y_agentes(api_client, user_factory, tenant_schema):
    cambiar_rol(tenant_schema, 'viewer', quitar=['ai.access'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    for resp in (api_client.post(CHAT_URL, {'prompt': 'Hola'}, format='json'),
                 api_client.get(AGENTS_URL)):
        assert resp.status_code == 403
        assert resp.json()['required_permission'] == 'ai.access'


def test_rol_con_ai_access_entra(api_client, user_factory):
    api_client.force_authenticate(user=user_factory(role='viewer'))
    assert api_client.get(AGENTS_URL).status_code == 200


# ---------------------------------------------------------------------------
# Herramientas
# ---------------------------------------------------------------------------


@pytest.fixture
def cartera(tenant_schema):
    """Un cliente con un préstamo activo y una cuota vencida."""
    from apps.loans.models import Customer, Loan, LoanSchedule

    cliente = Customer.objects.create(
        first_name='Rosa', last_name='Ventura', date_of_birth=date(1985, 3, 3), gender='F',
        email='rosa@crediflux.test', phone='+18095551234', address_line1='Calle 3',
        city='Santo Domingo', state='DN', postal_code='10101', id_type='cedula',
        id_number='001-7654321-0', employment_status='employed',
    )
    prestamo = Loan.objects.create(
        customer=cliente, loan_type='personal', principal_amount=Money(Decimal('25000.00'), 'DOP'),
        interest_rate=Decimal('5.00'), interest_type='french', term_months=6,
        payment_frequency='monthly', payment_amount=Money(Decimal('1.00'), 'DOP'), status='active',
        disbursement_date=date(2026, 1, 1), first_payment_date=date(2026, 2, 1),
    )
    LoanSchedule.objects.create(
        loan=prestamo, installment_number=1, due_date=date(2026, 2, 1),
        total_amount=Money(Decimal('4500.00'), 'DOP'), principal_amount=Money(Decimal('4000.00'), 'DOP'),
        interest_amount=Money(Decimal('500.00'), 'DOP'), status='overdue',
    )
    return cliente, prestamo


def _llamar(user, herramienta, *args):
    with con_usuario(user):
        return herramienta(*args)


def test_sin_usuario_las_herramientas_con_datos_se_niegan(cartera):
    cliente, _ = cartera
    assert tools.buscar_cliente('Rosa') == 'No tienes permiso para ver clientes.'
    assert tools.dashboard_resumen() == 'No tienes permiso para ver préstamos.'


def test_con_permisos_las_herramientas_devuelven_datos(user_factory, cartera):
    cliente, prestamo = cartera
    user = user_factory(role='viewer')
    assert 'Ventura' in _llamar(user, tools.buscar_cliente, 'Ventura')
    resumen = _llamar(user, tools.resumen_cliente, cliente.customer_id)
    assert prestamo.loan_number in resumen and 'Total pagado' in resumen
    assert prestamo.loan_number in _llamar(user, tools.clientes_en_mora)
    assert 'Cartera total: RD$ 25,000.00' in _llamar(user, tools.dashboard_resumen)
    assert 'Puntaje total' in _llamar(user, tools.analizar_riesgo_cliente, cliente.customer_id)


def test_sin_loans_view_ninguna_herramienta_devuelve_prestamos(user_factory, tenant_schema, cartera):
    cliente, prestamo = cartera
    cambiar_rol(tenant_schema, 'viewer', quitar=['loans.view'])
    user = user_factory(role='viewer')

    resumen = _llamar(user, tools.resumen_cliente, cliente.customer_id)
    assert 'Ventura' in resumen  # el cliente sí (customers.view)
    assert prestamo.loan_number not in resumen
    assert 'No tienes permiso para ver préstamos.' in resumen
    for salida in (
        _llamar(user, tools.clientes_en_mora),
        _llamar(user, tools.dashboard_resumen),
        _llamar(user, tools.analizar_riesgo_cliente, cliente.customer_id),
        _llamar(user, tools.proyeccion_cobros, 7),
    ):
        assert salida == 'No tienes permiso para ver préstamos.'


def test_sin_customers_view_no_busca_clientes(user_factory, tenant_schema, cartera):
    cambiar_rol(tenant_schema, 'viewer', quitar=['customers.view'])
    user = user_factory(role='viewer')
    assert _llamar(user, tools.buscar_cliente, 'Rosa') == 'No tienes permiso para ver clientes.'
    assert _llamar(user, tools.clientes_en_mora) == 'No tienes permiso para ver clientes.'


def test_sin_payments_view_el_resumen_no_trae_pagos(user_factory, tenant_schema, cartera):
    cliente, _ = cartera
    cambiar_rol(tenant_schema, 'viewer', quitar=['payments.view'])
    user = user_factory(role='viewer')
    resumen = _llamar(user, tools.resumen_cliente, cliente.customer_id)
    assert 'Total pagado' not in resumen and 'No tienes permiso para ver pagos.' in resumen
    tablero = _llamar(user, tools.dashboard_resumen)
    assert 'Cobros realizados' not in tablero and 'No tienes permiso para ver pagos.' in tablero


def test_el_chat_ata_las_herramientas_al_usuario_de_la_peticion(
    api_client, user_factory, tenant_schema, cartera
):
    """ChatView fija el usuario mientras el agente trabaja: la herramienta mide sus permisos."""
    cambiar_rol(tenant_schema, 'viewer', quitar=['loans.view'])
    salidas = []

    def _handle(self, prompt):
        salidas.append(tools.dashboard_resumen())
        return SimpleNamespace(text='ok', conversation_id=None, thinking=None, usage=None)

    api_client.force_authenticate(user=user_factory(role='viewer'))
    with override_settings(AI_ENABLED=True), \
            mock.patch('apps.ai.agents.CrediFluxAssistant.handle', _handle), \
            mock.patch('apps.ai.agents.CrediFluxAssistant.start_conversation',
                       return_value=SimpleNamespace(id='c0nv')):
        resp = api_client.post(CHAT_URL, {'prompt': 'Hola'}, format='json')
    assert resp.status_code == 200, resp.content
    assert salidas == ['No tienes permiso para ver préstamos.']
    # Fuera de la petición no queda usuario fijado.
    assert tools.dashboard_resumen() == 'No tienes permiso para ver préstamos.'
