"""Matriz de autorización por rol (caracterización antes de los roles editables, D6).

Recorre `CASES` × personas de `tests/authz_cases.py`: crea un usuario por
persona en el tenant de pruebas, lo autentica y comprueba que el código de
respuesta está en `EXPECTED`. En los casos de alcance comprueba además si la
respuesta incluye el objeto de otro usuario (`VISIBLE`).

Dueños (`owner`, `owner_viewer`) y admin se crean con 2FA activa para que la matriz no cambie de sentido
cuando la 2FA sea obligatoria en esos roles.
"""

import string
from datetime import date
from decimal import Decimal
from itertools import count

import pyotp
import pytest
from django.utils import timezone
from moneyed import Money

from tests.authz_cases import (
    CASES, EXPECTED, EXTRA_SETUP, PERSONAS, SCOPE_OBJECT, VISIBLE,
)

_seq = count(1)

# Política que no estorba al desembolso (como PERMISSIVE_POLICY de apps/loans/tests/conftest.py),
# con la segregación aprobación/desembolso encendida: es lo que fija el caso del maker-checker.
POLITICA_PERMISIVA = {
    'max_loan_amount': Money(Decimal('100000000.00'), 'DOP'),
    'max_interest_rate': Decimal('600.00'),
    'max_loan_term_months': 600,
    'require_guarantor': False,
    'guarantor_required_above': None,
    'require_collateral_default': False,
    'require_id_document': False,
    'require_credit_score': False,
    'require_disbursement_approval': True,
    'max_active_loans_per_customer': 99,
}


# ---------------------------------------------------------------------------
# Personas y objetos
# ---------------------------------------------------------------------------


def _persona(user_factory, persona):
    if persona == 'owner':
        # Como lo crea el registro del tenant: dueño con rol admin.
        return user_factory(role='admin', is_tenant_owner=True,
                            is_2fa_enabled=True, totp_secret=pyotp.random_base32())
    if persona == 'owner_viewer':
        # Dueño sin rol admin: fija el bypass de dueño por separado del rol.
        return user_factory(role='viewer', is_tenant_owner=True,
                            is_2fa_enabled=True, totp_secret=pyotp.random_base32())
    if persona == 'admin':
        return user_factory(role='admin', is_2fa_enabled=True, totp_secret=pyotp.random_base32())
    return user_factory(role=persona)


def _cliente():
    from apps.loans.models import Customer

    n = next(_seq)
    return Customer.objects.create(
        first_name='Juana', last_name=f'Matriz {n}', date_of_birth=date(1990, 1, 1),
        gender='F', email=f'matriz{n}@crediflux.test', phone='+18095550000',
        address_line1='Calle 1', city='Santo Domingo', state='DN', postal_code='10101',
        id_type='cedula', id_number=f'002-{n:07d}-1', employment_status='employed',
    )


def _prestamo(**overrides):
    from apps.loans.models import Loan

    data = {
        'customer': _cliente(),
        'loan_type': 'personal',
        'principal_amount': Money(Decimal('10000.00'), 'DOP'),
        'interest_rate': Decimal('5.00'),
        'interest_type': 'french',
        'term_months': 6,
        'payment_frequency': 'monthly',
        'payment_amount': Money(Decimal('1.00'), 'DOP'),
        'status': 'active',
        'disbursement_date': date(2026, 1, 1),
        'first_payment_date': date(2026, 2, 1),
    }
    data.update(overrides)
    loan = Loan.objects.create(**data)
    loan.outstanding_balance = loan.principal_amount
    loan.save()
    return loan


def _prestamo_activo(ctx):
    return _prestamo()


def _prestamo_aprobado_por_mi(ctx):
    """Aprobado por quien va a desembolsar, con contrato firmado: sólo falta el maker-checker."""
    from apps.loans.models_contracts import Contract

    loan = _prestamo(status='approved', disbursement_date=None, approved_by=ctx['actor'])
    Contract.objects.create(
        loan=loan, content='Contrato de la matriz', status='pending_signature',
        customer_signed_at=timezone.now(),
    )
    return loan


def _pago_completado(ctx):
    from apps.loans.models import LoanPayment

    return LoanPayment.objects.create(
        loan=_prestamo(), amount=Money(Decimal('500.00'), 'DOP'),
        payment_method='bank_transfer', status='completed', created_by=ctx['otro'],
    )


def _caja_con_turnos(ctx):
    from apps.cashbox.models import CashRegister, CashSession

    n = next(_seq)
    register = CashRegister.objects.create(name=f'Caja Matriz {n}', code=f'CAJA-MTZ-{n}')
    CashSession.objects.create(
        register=register, cashier=ctx['otro'], opening_balance=Decimal('1000.00'), status='closed',
    )
    return register


def _turno_cerrado(ctx):
    return _caja_con_turnos(ctx).sessions.get()


def _usuario_destino(ctx):
    return ctx['user_factory'](role='viewer')


def _dueno_destino(ctx):
    return ctx['user_factory'](role='admin', is_tenant_owner=True)


def _rol_propio(ctx):
    """Rol propio de la financiera con un código que tienen todos los que pasan el permiso;
    la ruta usa su clave."""
    from apps.users.models import Role

    return Role.objects.create(
        tenant=ctx['tenant'], key=f'rol-matriz-{next(_seq)}', name='Rol de la matriz',
        permissions=['loans.view'],
    ).key


def _visita_ajena(ctx):
    from apps.loans.models_geolocation import CollectorVisit

    return CollectorVisit.objects.create(
        collector=ctx['user_factory'](role='collector'), customer=_cliente(),
        latitude=Decimal('18.4861000'), longitude=Decimal('-69.9312000'),
    )


def _ubicacion_ajena(ctx):
    from apps.loans.models_geolocation import CollectorLocation

    return CollectorLocation.objects.create(
        collector=ctx['user_factory'](role='collector'),
        latitude=Decimal('18.4861000'), longitude=Decimal('-69.9312000'),
    )


def _registro_auditoria(ctx):
    from apps.audit.models import AuditLog

    return AuditLog.log(
        tenant=ctx['tenant'], user=ctx['otro'], action='create', model_name='Customer',
        object_repr='registro de la matriz',
    )


def _politica_permisiva(ctx):
    tenant = ctx['tenant']
    ctx['restaurar'] = {field: getattr(tenant, field) for field in POLITICA_PERMISIVA}
    for field, value in POLITICA_PERMISIVA.items():
        setattr(tenant, field, value)
    tenant.save()
    return tenant


OBJETOS = {
    'prestamo_activo': _prestamo_activo,
    'prestamo_aprobado_por_mi': _prestamo_aprobado_por_mi,
    'pago_completado': _pago_completado,
    'caja_con_turnos': _caja_con_turnos,
    'turno_cerrado': _turno_cerrado,
    'usuario_destino': _usuario_destino,
    'dueno_destino': _dueno_destino,
    'rol_propio': _rol_propio,
    'visita_ajena': _visita_ajena,
    'ubicacion_ajena': _ubicacion_ajena,
    'registro_auditoria': _registro_auditoria,
    'politica_permisiva': _politica_permisiva,
}


def _marcadores(path):
    return [field for _, field, _, _ in string.Formatter().parse(path) if field]


def _ids(response):
    data = response.json()
    rows = data.get('results', data) if isinstance(data, dict) else data
    return {str(row['id']) for row in rows}


# ---------------------------------------------------------------------------
# La matriz
# ---------------------------------------------------------------------------


def test_la_matriz_cubre_todos_los_casos():
    assert set(EXPECTED) == {case[0] for case in CASES}
    assert set(VISIBLE) == set(SCOPE_OBJECT)
    for name, fields in EXTRA_SETUP.items():
        assert name in EXPECTED
        assert set(fields) <= set(OBJETOS)
    for _, _, path, _ in CASES:
        assert set(_marcadores(path)) <= set(OBJETOS), path


@pytest.mark.parametrize('persona', PERSONAS)
@pytest.mark.parametrize('case', CASES, ids=[case[0] for case in CASES])
def test_matriz_de_autorizacion(case, persona, api_client, user_factory, tenant_schema):
    name, method, path, body = case
    actor = _persona(user_factory, persona)
    ctx = {
        'actor': actor,
        'otro': user_factory(role='viewer'),
        'tenant': tenant_schema,
        'user_factory': user_factory,
    }
    objetos = {}
    try:
        for field in _marcadores(path) + EXTRA_SETUP.get(name, []):
            objetos[field] = OBJETOS[field](ctx)
        url = path.format(**{k: getattr(v, 'pk', v) for k, v in objetos.items()})

        api_client.force_authenticate(user=actor)
        response = getattr(api_client, method.lower())(url, body, format='json')
    finally:
        # La BD se revierte sola; el objeto de sesión del tenant en memoria no.
        for field, value in ctx.get('restaurar', {}).items():
            setattr(tenant_schema, field, value)

    assert response.status_code in EXPECTED[name][persona], (
        f'{name} como {persona}: {response.status_code} {response.content[:300]!r}'
    )

    if name in VISIBLE:
        objeto = objetos[SCOPE_OBJECT[name]]
        assert (str(objeto.pk) in _ids(response)) is VISIBLE[name][persona], (
            f'{name} como {persona}: alcance distinto del esperado'
        )
