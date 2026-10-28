"""Task 14: revertir un pago exige `payments.void`, motivo y el TOTP de un autorizador.

El autorizador es el dueño de la financiera o un usuario con rol `admin`, activo y con 2FA,
de la misma financiera (puede ser quien revierte; el código se pide igual). Tres códigos malos
por autorizador lo bloquean 15 minutos (`revert_auth_fail:{pk}`); un autorizador inválido
responde 400 en `authorizer_id` sin contar fallo.
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

import pyotp
import pytest
from django.core.cache import cache
from moneyed import Money

# Instante fijo para que el código generado y la verificación caigan en el mismo paso de 30 s.
AHORA = 1_900_000_015


@pytest.fixture(autouse=True)
def _cache_limpia():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def reloj():
    """Congela el reloj de `apps.users.totp`; `reloj.avanzar(s)` mueve el instante."""
    estado = SimpleNamespace(t=AHORA)
    falso = SimpleNamespace(time=lambda: estado.t)
    with mock.patch('apps.users.totp.time', falso):
        estado.avanzar = lambda s: setattr(estado, 't', estado.t + s)
        yield estado


def _codigo(user, reloj, desfase=0):
    return pyotp.TOTP(user.totp_secret).at(reloj.t + desfase)


def _malo(user, reloj):
    bueno = _codigo(user, reloj)
    return f'{(int(bueno) + 1) % 1_000_000:06d}'


@pytest.fixture
def autorizador(user_factory):
    return user_factory(role='admin', is_2fa_enabled=True, totp_secret=pyotp.random_base32())


@pytest.fixture
def gerente(user_factory):
    """Quien revierte: el rol `manager` tiene `payments.void` por defecto."""
    return user_factory(role='manager')


@pytest.fixture
def cliente(api_client, gerente):
    api_client.force_authenticate(user=gerente)
    api_client.user = gerente
    return api_client


def _pago(loan, user=None, metodo='bank_transfer'):
    from apps.loans.models import LoanPayment

    return LoanPayment.objects.create(
        loan=loan, amount=Money(Decimal('500.00'), 'DOP'), payment_method=metodo,
        status='completed', created_by=user,
    )


@pytest.fixture
def pago(active_loan, admin_user):
    return _pago(active_loan, admin_user)


def _revertir(client, payment, **body):
    datos = {'reason': 'Pago duplicado', **body}
    return client.post(f'/api/loans/payments/{payment.id}/reverse/', datos, format='json')


def _fallos(user):
    return cache.get(f'revert_auth_fail:{user.pk}')


# ---------------------------------------------------------------------------
# Camino feliz
# ---------------------------------------------------------------------------


def test_admin_con_2fa_y_codigo_valido_revierte_y_audita(cliente, pago, autorizador, reloj, tenant):
    from apps.audit.models import AuditLog

    resp = _revertir(cliente, pago, authorizer_id=autorizador.id, code=_codigo(autorizador, reloj))

    assert resp.status_code == 200, resp.content
    pago.refresh_from_db()
    assert pago.status == 'reversed'
    assert pago.reversed_by == cliente.user
    log = AuditLog.objects.get(action='payment_void', object_id=str(pago.id))
    assert log.user == cliente.user
    assert log.extra_data['authorized_by'] == {
        'id': autorizador.id, 'name': autorizador.get_full_name(),
    }
    assert _fallos(autorizador) is None


def test_reverso_en_efectivo_saca_la_caja(api_client, admin_user, gerente, autorizador, active_loan, reloj):
    from apps.cashbox.models import CashMovement, CashRegister, CashSession
    from apps.cashbox.services import record_payment_inflow

    sesion = CashSession.objects.create(
        register=CashRegister.objects.create(name='Caja Principal', code='CAJA-01'),
        cashier=admin_user, opening_balance=Money(Decimal('20000.00'), 'DOP'), status='open',
    )
    pago = _pago(active_loan, admin_user, metodo='cash')
    assert record_payment_inflow(pago, admin_user)

    api_client.force_authenticate(user=gerente)
    resp = _revertir(api_client, pago, authorizer_id=autorizador.id, code=_codigo(autorizador, reloj))

    assert resp.status_code == 200, resp.content
    salida = CashMovement.objects.get(movement_type='outflow', loan_payment=pago)
    assert salida.category == 'refund'
    assert salida.session == sesion
    assert salida.amount == Money(Decimal('500.00'), 'DOP')


def test_el_autorizador_puede_ser_quien_revierte(api_client, autorizador, pago, reloj):
    api_client.force_authenticate(user=autorizador)

    sin_codigo = _revertir(api_client, pago, authorizer_id=autorizador.id)
    assert sin_codigo.status_code == 400
    assert 'code' in sin_codigo.json()

    resp = _revertir(api_client, pago, authorizer_id=autorizador.id, code=_codigo(autorizador, reloj))
    assert resp.status_code == 200, resp.content


def test_el_dueno_con_2fa_autoriza(cliente, admin_user, pago, reloj):
    admin_user.is_2fa_enabled = True
    admin_user.totp_secret = pyotp.random_base32()
    admin_user.role = 'viewer'  # dueño aunque su rol no sea admin
    admin_user.save()

    resp = _revertir(cliente, pago, authorizer_id=admin_user.id, code=_codigo(admin_user, reloj))
    assert resp.status_code == 200, resp.content


# ---------------------------------------------------------------------------
# Anti-replay y bloqueo
# ---------------------------------------------------------------------------


def test_el_mismo_codigo_no_sirve_dos_veces(cliente, autorizador, active_loan, admin_user, reloj):
    primero, segundo = _pago(active_loan, admin_user), _pago(active_loan, admin_user)
    codigo = _codigo(autorizador, reloj)

    assert _revertir(cliente, primero, authorizer_id=autorizador.id, code=codigo).status_code == 200
    resp = _revertir(cliente, segundo, authorizer_id=autorizador.id, code=codigo)

    assert resp.status_code == 400
    assert resp.json() == {'code': ['Código incorrecto. Quedan 2 intentos.']}
    segundo.refresh_from_db()
    assert segundo.status == 'completed'


def test_tres_codigos_malos_bloquean_15_minutos(cliente, autorizador, pago, reloj):
    from apps.audit.models import AuditLog

    for quedan in (2, 1, 0):
        resp = _revertir(cliente, pago, authorizer_id=autorizador.id, code=_malo(autorizador, reloj))
        assert resp.status_code == 400
        assert resp.json() == {'code': [f'Código incorrecto. Quedan {quedan} intentos.']}

    resp = _revertir(cliente, pago, authorizer_id=autorizador.id, code=_codigo(autorizador, reloj))
    assert resp.status_code == 429
    assert resp.json() == {'detail': 'Autorización bloqueada 15 minutos por intentos fallidos.'}
    pago.refresh_from_db()
    assert pago.status == 'completed'

    fallidos = AuditLog.objects.filter(action='payment_void_auth_failed', object_id=str(pago.id))
    assert fallidos.count() == 3
    for log in fallidos:
        assert log.user == cliente.user
        assert log.extra_data['authorizer_id'] == autorizador.id
        assert 'code' not in log.extra_data
        assert _codigo(autorizador, reloj) not in str(log.extra_data)

    # Pasada la ventana (la clave caduca a los 900 s), vuelve a aceptar.
    cache.delete(f'revert_auth_fail:{autorizador.pk}')
    reloj.avanzar(30)
    resp = _revertir(cliente, pago, authorizer_id=autorizador.id, code=_codigo(autorizador, reloj))
    assert resp.status_code == 200, resp.content


def test_la_ventana_del_bloqueo_es_de_900_segundos(cliente, autorizador, pago, reloj):
    with mock.patch('apps.users.lockout.cache.add', wraps=cache.add) as add:
        _revertir(cliente, pago, authorizer_id=autorizador.id, code=_malo(autorizador, reloj))
    add.assert_any_call(f'revert_auth_fail:{autorizador.pk}', 0, 900)


def test_un_acierto_borra_los_fallos(cliente, autorizador, active_loan, admin_user, reloj):
    pago = _pago(active_loan, admin_user)
    _revertir(cliente, pago, authorizer_id=autorizador.id, code=_malo(autorizador, reloj))
    assert _fallos(autorizador) == 1

    assert _revertir(
        cliente, pago, authorizer_id=autorizador.id, code=_codigo(autorizador, reloj)
    ).status_code == 200
    assert _fallos(autorizador) is None


# ---------------------------------------------------------------------------
# Autorizador inválido: 400 en authorizer_id, sin contar fallo
# ---------------------------------------------------------------------------


def _otra_financiera():
    """Financiera sin schema (sus usuarios viven en public); vuelve al schema de pruebas."""
    from django.db import connection

    from apps.tenants.models import Tenant

    actual = connection.tenant
    connection.set_schema_to_public()
    otra = Tenant(schema_name='otra_rev', name='Otra', business_name='Otra SRL',
                  email='otra_rev@financiera.test')
    otra.auto_create_schema = False
    otra.save()
    connection.set_tenant(actual)
    return otra


@pytest.mark.parametrize('caso', ['inactivo', 'sin_2fa', 'sin_secreto', 'gerente', 'otra_financiera'])
def test_autorizador_invalido_responde_400_sin_contar(cliente, user_factory, pago, reloj, caso):
    secreto = pyotp.random_base32()
    datos = {'role': 'admin', 'is_2fa_enabled': True, 'totp_secret': secreto}
    if caso == 'inactivo':
        datos['is_active'] = False
    elif caso == 'sin_2fa':
        datos['is_2fa_enabled'] = False
    elif caso == 'sin_secreto':
        datos['totp_secret'] = None
    elif caso == 'gerente':
        datos['role'] = 'manager'
    elif caso == 'otra_financiera':
        datos['tenant'] = _otra_financiera()
    invalido = user_factory(**datos)
    codigo = pyotp.TOTP(secreto).at(reloj.t)

    resp = _revertir(cliente, pago, authorizer_id=invalido.id, code=codigo)

    assert resp.status_code == 400
    assert 'authorizer_id' in resp.json()
    assert _fallos(invalido) is None
    pago.refresh_from_db()
    assert pago.status == 'completed'


@pytest.mark.parametrize('valor', [None, '', 99_999_999, 'abc'])
def test_autorizador_ausente_o_inexistente(cliente, pago, reloj, valor):
    body = {'code': '123456'}
    if valor is not None:
        body['authorizer_id'] = valor
    resp = _revertir(cliente, pago, **body)

    assert resp.status_code == 400
    assert 'authorizer_id' in resp.json()


def test_el_motivo_va_antes_que_el_autorizador(cliente, pago):
    resp = cliente.post(f'/api/loans/payments/{pago.id}/reverse/', {}, format='json')
    assert resp.status_code == 400
    assert 'authorizer_id' not in resp.json()


# ---------------------------------------------------------------------------
# Permiso
# ---------------------------------------------------------------------------


def test_sin_payments_void_403(api_client, user_factory, autorizador, pago, reloj):
    api_client.force_authenticate(user=user_factory(role='cashier'))  # registra, no anula

    resp = _revertir(api_client, pago, authorizer_id=autorizador.id, code=_codigo(autorizador, reloj))

    assert resp.status_code == 403
    assert resp.json()['required_permission'] == 'payments.void'
    pago.refresh_from_db()
    assert pago.status == 'completed'


# ---------------------------------------------------------------------------
# GET /api/users/authorizers/
# ---------------------------------------------------------------------------


def test_autorizadores_lista_solo_dueno_y_admins_con_2fa(cliente, user_factory, admin_user, autorizador):
    secreto = pyotp.random_base32()
    admin_user.is_2fa_enabled, admin_user.totp_secret = True, secreto
    admin_user.save()
    user_factory(role='admin')  # sin 2FA
    user_factory(role='manager', is_2fa_enabled=True, totp_secret=secreto)
    user_factory(role='admin', is_2fa_enabled=True, totp_secret=secreto, is_active=False)
    user_factory(role='admin', is_2fa_enabled=True, totp_secret=secreto, tenant=_otra_financiera())

    resp = cliente.get('/api/users/authorizers/')

    assert resp.status_code == 200, resp.content
    filas = {f['id']: f for f in resp.json()}
    assert set(filas) == {admin_user.id, autorizador.id}
    assert filas[autorizador.id] == {
        'id': autorizador.id, 'full_name': autorizador.get_full_name(),
        'role_label': autorizador.get_role_display(),
    }
    assert filas[admin_user.id]['role_label'] == 'Dueño'


def test_autorizadores_exige_payments_void(api_client, user_factory):
    api_client.force_authenticate(user=user_factory(role='cashier'))

    resp = api_client.get('/api/users/authorizers/')

    assert resp.status_code == 403
    assert resp.json()['required_permission'] == 'payments.void'


def test_lockout_generalizado_no_cambia_la_ventana_del_login():
    from apps.users import lockout

    with mock.patch('apps.users.lockout.cache.add', wraps=cache.add) as add:
        lockout._increment('login_fail:x')
    add.assert_called_once_with('login_fail:x', 0, lockout.LOGIN_FAIL_WINDOW)


# ---------------------------------------------------------------------------
# Fix ronda 1: doble reverso, bloqueo de 15 minutos exactos, bloqueo antes del formato
# ---------------------------------------------------------------------------


def _pago_en_efectivo_con_caja(active_loan, admin_user):
    from apps.cashbox.models import CashRegister, CashSession
    from apps.cashbox.services import record_payment_inflow

    CashSession.objects.create(
        register=CashRegister.objects.create(name='Caja Principal', code='CAJA-01'),
        cashier=admin_user, opening_balance=Money(Decimal('20000.00'), 'DOP'), status='open',
    )
    pago = _pago(active_loan, admin_user, metodo='cash')
    assert record_payment_inflow(pago, admin_user)
    return pago


def test_un_segundo_reverso_con_lectura_vieja_no_saca_la_caja_dos_veces(
    cliente, autorizador, active_loan, admin_user, reloj
):
    """Carrera: la 2.ª petición leyó el pago 'completed' antes de que la 1.ª lo reversara."""
    from apps.cashbox.models import CashMovement
    from apps.loans.models import LoanPayment
    from apps.loans.views import LoanPaymentViewSet

    pago = _pago_en_efectivo_con_caja(active_loan, admin_user)
    vieja = LoanPayment.objects.get(pk=pago.pk)  # lectura previa al primer reverso

    assert _revertir(
        cliente, pago, authorizer_id=autorizador.id, code=_codigo(autorizador, reloj)
    ).status_code == 200

    reloj.avanzar(30)  # código nuevo y válido: la autorización pasa
    with mock.patch.object(LoanPaymentViewSet, 'get_object', return_value=vieja):
        resp = _revertir(cliente, pago, authorizer_id=autorizador.id, code=_codigo(autorizador, reloj))

    assert resp.status_code == 400
    assert resp.json() == {'error': 'El pago ya ha sido reversado'}
    assert CashMovement.objects.filter(movement_type='outflow', loan_payment=pago).count() == 1


def test_el_reverso_bloquea_el_pago_con_select_for_update(cliente, autorizador, pago, reloj):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as ctx:
        resp = _revertir(cliente, pago, authorizer_id=autorizador.id, code=_codigo(autorizador, reloj))

    assert resp.status_code == 200, resp.content
    assert any(
        'FOR UPDATE' in q['sql'] and 'loan_payments' in q['sql'] for q in ctx.captured_queries
    ), [q['sql'] for q in ctx.captured_queries if 'FOR UPDATE' in q['sql']]


def test_el_bloqueo_dura_15_minutos_desde_el_tercer_fallo(cliente, autorizador, pago, reloj):
    clave = f'revert_auth_fail:{autorizador.pk}'
    with mock.patch('apps.users.lockout.cache.touch', wraps=cache.touch) as touch:
        for _ in range(2):
            _revertir(cliente, pago, authorizer_id=autorizador.id, code=_malo(autorizador, reloj))
        touch.assert_not_called()
        _revertir(cliente, pago, authorizer_id=autorizador.id, code=_malo(autorizador, reloj))
        touch.assert_called_once_with(clave, 900)
        # Los intentos ya bloqueados no reinician la ventana.
        _revertir(cliente, pago, authorizer_id=autorizador.id, code=_codigo(autorizador, reloj))
        touch.assert_called_once()


@pytest.mark.parametrize('codigo', ['', 'abc', '12345'])
def test_bloqueado_responde_429_aun_con_codigo_mal_escrito(cliente, autorizador, pago, reloj, codigo):
    for _ in range(3):
        _revertir(cliente, pago, authorizer_id=autorizador.id, code=_malo(autorizador, reloj))

    resp = _revertir(cliente, pago, authorizer_id=autorizador.id, code=codigo)

    assert resp.status_code == 429
    assert _fallos(autorizador) == 3  # el código mal escrito no cuenta


def test_codigo_mal_escrito_sin_bloqueo_no_cuenta(cliente, autorizador, pago):
    resp = _revertir(cliente, pago, authorizer_id=autorizador.id, code='12a456')

    assert resp.status_code == 400
    assert 'code' in resp.json()
    assert _fallos(autorizador) is None
