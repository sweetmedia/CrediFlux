"""
Core views
"""
import re
import time

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import connection
from django.db.models import Q


class HealthCheckView(APIView):
    """
    Health check endpoint for monitoring
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Check application health"""
        try:
            # Check database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

            return Response({
                'status': 'healthy',
                'database': 'connected'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'status': 'unhealthy',
                'error': str(e)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# RNC Validation Views
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.settings import api_settings
from rest_framework.throttling import BaseThrottle, ScopedRateThrottle, SimpleRateThrottle
from apps.core.services.rnc_lookup import validate_rnc, is_rnc_database_loaded, RNCLookupService
from apps.core.permissions import TenantMatches
from apps.users.authz import MENSAJE_DENEGADO, ViewPermissionRequired, has_perm
from django.core.cache import cache as default_cache
from django.core.exceptions import ImproperlyConfigured
import logging

logger = logging.getLogger(__name__)


class CanLookupCedula(BasePermission):
    """
    Consulta del Padrón JCE: es dato personal, así que exige customers.create o customers.edit
    (quien da de alta o corrige la ficha del cliente), también en GET. Cambio intencional D5 (R8):
    cobrador y supervisor de cobros ya no consultan el padrón con sus permisos por defecto.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if has_perm(user, 'customers.create') or has_perm(user, 'customers.edit'):
            return True
        raise PermissionDenied({'detail': MENSAJE_DENEGADO, 'required_permission': 'customers.create'})


def _buscar_en_padron(cedula):
    """Una fila de public.padron_jce o None. Consulta calificada: no toca el search_path de la conexión."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT cedula, nombres, apellido1, apellido2, fecha_nacimiento, "
            "sexo, estado_civil, lugar_nacimiento "
            "FROM public.padron_jce WHERE cedula = %s LIMIT 1",
            [cedula]
        )
        return cursor.fetchone()


def _auditar_consulta_cedula(request, cedula, found):
    """Deja constancia de quién consultó qué cédula; sin datos personales del padrón."""
    from apps.audit.models import AuditLog
    from apps.audit.middleware import get_client_ip, get_user_agent
    AuditLog.log(
        tenant=getattr(request, 'tenant', None),
        user=request.user,
        action='cedula_lookup',
        model_name='PadronJCE',
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_data={'cedula': cedula, 'found': found},
    )


class TopesPadronThrottle(BaseThrottle):
    """Topes de consultas al padrón (run-8 M1, R22): por minuto y por día del usuario, y por día
    de la financiera. Se revisan los tres y la consulta sólo se anota en los tres si todos la dejan
    pasar: un rechazo de uno no gasta el cupo de los otros (con throttles separados DRF anota en
    los que sí dejan pasar, y un usuario podía agotar el tope de toda la financiera). Una tasa que
    falte en DEFAULT_THROTTLE_RATES es un error de configuración, no un tope apagado. La tasa se
    lee en cada request para que `override_settings` la cambie en los tests."""

    cache = default_cache
    timer = time.time
    VENTANAS = (
        ('cedula_lookup', lambda request: request.user.pk),
        ('cedula_lookup_day', lambda request: request.user.pk),
        ('cedula_lookup_tenant_day', lambda request: (
            request.user.tenant_id
            or getattr(getattr(request, 'tenant', None), 'pk', None)
            or f'user-{request.user.pk}'
        )),
    )

    def _ventanas(self, request):
        tasas = api_settings.DEFAULT_THROTTLE_RATES
        for scope, ident in self.VENTANAS:
            tasa = tasas.get(scope)
            if not tasa:
                raise ImproperlyConfigured(f'Falta la tasa «{scope}» en DEFAULT_THROTTLE_RATES.')
            num, duracion = SimpleRateThrottle.parse_rate(None, tasa)
            yield f'throttle_{scope}_{ident(request)}', num, duracion

    def allow_request(self, request, view):
        ahora = self.timer()
        revisadas, espera = [], 0
        for clave, num, duracion in self._ventanas(request):
            historia = [t for t in self.cache.get(clave, []) if t > ahora - duracion]
            if len(historia) >= num:
                espera = max(espera, duracion - (ahora - historia[-1]))
            revisadas.append((clave, historia, duracion))
        if espera:
            self._espera = espera
            return False
        for clave, historia, duracion in revisadas:
            self.cache.set(clave, [ahora] + historia, duracion)
        return True

    def wait(self):
        return getattr(self, '_espera', None)


CEDULA_INVALIDA = 'Cédula inválida: debe tener exactamente 11 dígitos.'


def _normalizar_cedula(valor):
    """Los 11 dígitos de la cédula (sin guiones ni espacios) o None si no los tiene."""
    cedula = re.sub(r'[-\s]', '', valor or '')
    return cedula if re.fullmatch(r'[0-9]{11}', cedula) else None


@api_view(['GET'])
@permission_classes([IsAuthenticated, TenantMatches, CanLookupCedula])
@throttle_classes([TopesPadronThrottle])
def validate_cedula_view(request):
    """
    Busca una cédula en el Padrón JCE (~7.9M registros).
    GET /api/core/validate-cedula/?cedula=00112345678
    """
    # Sólo 11 dígitos (run-8 L3): nada más se consulta ni se guarda en la auditoría.
    cedula = _normalizar_cedula(request.query_params.get('cedula', ''))
    if cedula is None:
        return Response({'detail': CEDULA_INVALIDA}, status=status.HTTP_400_BAD_REQUEST)

    try:
        row = _buscar_en_padron(cedula)
        # Sin constancia no hay dato: si la auditoría falla, no se entrega la información.
        _auditar_consulta_cedula(request, cedula, found=row is not None)
    except Exception as exc:
        # Sólo el tipo de la excepción: sin texto ni traceback (puede arrastrar datos personales).
        logger.error('Fallo consultando el padrón JCE: %s', type(exc).__name__)
        return Response(
            {'detail': 'No se pudo consultar el padrón.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if row is None:
        return Response({
            'found': False,
            'cedula': cedula,
            'message': 'Cédula no encontrada en el Padrón JCE.',
        })

    cedula_raw, nombres, apellido1, apellido2, fecha_nac, sexo, estado_civil, lugar_nac = row
    nombres = nombres or ''
    apellido1 = apellido1 or ''
    apellido2 = apellido2 or ''
    cedula_fmt = cedula_raw
    if len(cedula_raw) == 11:
        cedula_fmt = f'{cedula_raw[:3]}-{cedula_raw[3:10]}-{cedula_raw[10]}'

    nombre_parts = nombres.split()
    first_name = nombre_parts[0].title() if nombre_parts else ''
    middle_name = ' '.join(nombre_parts[1:]).title() if len(nombre_parts) > 1 else ''
    apellidos = f"{apellido1.title()}{' ' + apellido2.title() if apellido2.strip() else ''}"

    return Response({
        'found': True,
        'cedula': cedula_fmt,
        'cedula_raw': cedula_raw,
        'nombres': nombres.title(),
        'first_name': first_name,
        'middle_name': middle_name,
        'apellido1': apellido1.title(),
        'apellido2': apellido2.title().strip(),
        'last_name': apellidos,
        'nombre_completo': f"{nombres.title()} {apellidos}",
        'fecha_nacimiento': str(fecha_nac) if fecha_nac else None,
        'sexo': (sexo or '').strip() or None,
        'estado_civil': (estado_civil or '').strip() or None,
        'lugar_nacimiento': (lugar_nac or '').strip() or None,
        'source': 'padron_jce',
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def validate_rnc_view(request):
    """
    API endpoint to validate an RNC or Cedula

    POST /api/validate-rnc/
    {
        "rnc": "00300749256"
    }

    Response:
    {
        "is_valid": true,
        "exists": true,
        "is_active": true,
        "data": {
            "rnc": "00300749256",
            "razon_social": "CASTALIO LEONIDAS RUIZ SANTANA",
            "actividad_economica": "PRÉSTAMO DE DINERO FUERA DEL SISTEMA BANCARIO",
            "fecha_inicio": "",
            "estado": "ACTIVO",
            "regimen_pago": "NORMAL",
            "is_active": true
        },
        "message": "RNC/Cédula encontrado"
    }
    """
    # Get RNC from request
    rnc = request.data.get('rnc', '').strip()

    if not rnc:
        return Response(
            {
                'is_valid': False,
                'exists': False,
                'is_active': False,
                'data': None,
                'message': 'RNC/Cédula es requerido',
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if database is loaded
    if not is_rnc_database_loaded():
        logger.warning('RNC database not loaded, returning database not available error')
        return Response(
            {
                'is_valid': None,
                'exists': None,
                'is_active': None,
                'data': None,
                'message': 'Base de datos de RNC no disponible. Por favor intente más tarde.',
                'database_loaded': False,
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    # Validate the RNC
    try:
        # El scraping en línea de la DGII queda sólo para usuarios autenticados.
        result = validate_rnc(rnc, allow_scrape=request.user.is_authenticated)

        # Log the lookup for monitoring
        if result['exists']:
            logger.info(f'RNC lookup: {rnc} - Found - Active: {result["is_active"]}')
        else:
            logger.info(f'RNC lookup: {rnc} - Not found')

        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f'Error validating RNC {rnc}: {str(e)}', exc_info=True)
        return Response(
            {
                'is_valid': False,
                'exists': False,
                'is_active': False,
                'data': None,
                'message': 'Error al validar RNC/Cédula',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def rnc_database_status(request):
    """
    Get the status of the RNC database

    GET /api/rnc-database-status/

    Response:
    {
        "loaded": true,
        "total_records": 752950,
        "last_updated": "2025-10-29 18:30:00"
    }
    """
    is_loaded = is_rnc_database_loaded()
    stats = RNCLookupService.get_database_stats()

    if is_loaded and stats:
        return Response(
            {
                'loaded': True,
                'total_records': stats.get('count'),
                'last_updated': stats.get('loaded_at'),
            },
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {
                'loaded': False,
                'total_records': 0,
                'last_updated': None,
                'message': 'Base de datos de RNC no cargada. Ejecute: python manage.py update_rnc_database'
            },
            status=status.HTTP_200_OK
        )


# @api_view no propaga throttle_scope a la vista envuelta: se fija en la clase generada.
validate_rnc_view.cls.throttle_scope = 'validate_rnc'
# Padrón JCE: datos personales de ~7.9M ciudadanos; límite propio por usuario.
rnc_database_status.cls.throttle_scope = 'validate_rnc'


# UI Theme Configuration View
@api_view(['GET'])
@permission_classes([AllowAny])
def get_ui_theme(request):
    """
    Get the current UI theme configuration

    GET /api/ui-theme/

    Response:
    {
        "theme": "v1",
        "version": "CrediFlux v1"
    }
    """
    from constance import config as constance_config

    theme = constance_config.UI_THEME
    theme_name = "CrediFlux v1" if theme == "v1" else "CrediFlux v2"

    return Response(
        {
            'theme': theme,
            'version': theme_name
        },
        status=status.HTTP_200_OK
    )


# Tenant Configuration View
@api_view(['GET'])
@permission_classes([AllowAny])
def get_tenant_config(request):
    """
    Get tenant configuration settings

    GET /api/config/

    Response:
    {
        "currency": "DOP",
        "currency_symbol": "RD$",
        "decimal_places": 2,
        "company_name": "Caproinsa SRL"
    }
    """
    # Get the current tenant from the request
    tenant = getattr(request, 'tenant', None)

    # Default values if no tenant is found (for public schema or non-tenant requests)
    if not tenant:
        return Response(
            {
                'currency': 'DOP',
                'currency_symbol': 'RD$',
                'decimal_places': 2,
                'company_name': 'CrediFlux',
            },
            status=status.HTTP_200_OK
        )

    # Return tenant-specific configuration
    return Response(
        {
            'currency': tenant.default_currency,
            'currency_symbol': tenant.currency_symbol,
            'decimal_places': 2,  # This could also be a tenant field if needed
            'company_name': tenant.business_name,
        },
        status=status.HTTP_200_OK
    )


class GlobalSearchView(APIView):
    """
    Global search across customers, loans, contracts, and payments.
    Uses django-tenants schema isolation - no need to filter by tenant.

    Abierta a cualquier miembro (`None`), pero cada sección sólo se llena si el usuario tiene
    el código que deja ver ese dato (`CODIGO_POR_SECCION`); sin él, la sección va vacía.
    """

    permission_classes = [IsAuthenticated, ViewPermissionRequired]
    permission_codes = {'GET': None}
    CODIGO_POR_SECCION = {
        'customers': 'customers.view',
        'loans': 'loans.view',
        'payments': 'payments.view',
        'contracts': 'contracts.view',
    }

    @staticmethod
    def _format_dominican_id(value):
        if not value:
            return ''

        cleaned = ''.join(ch for ch in str(value) if ch.isdigit())

        if len(cleaned) == 11:
            return f'{cleaned[:3]}-{cleaned[3:10]}-{cleaned[10:]}'

        if len(cleaned) == 9:
            return f'{cleaned[:1]}-{cleaned[1:3]}-{cleaned[3:8]}-{cleaned[8:]}'

        return value

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        results = {seccion: [] for seccion in self.CODIGO_POR_SECCION}

        if len(query) < 2:
            return Response({
                'query': query,
                'total_results': 0,
                'results': results,
                'message': 'La busqueda debe tener al menos 2 caracteres'
            })

        for seccion, codigo in self.CODIGO_POR_SECCION.items():
            if has_perm(request.user, codigo):
                results[seccion] = getattr(self, f'_buscar_{seccion}')(query)

        return Response({
            'query': query,
            'total_results': sum(len(v) for v in results.values()),
            'results': results,
        })

    def _buscar_customers(self, query):
        from apps.loans.models import Customer
        customers = Customer.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(id_number__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )[:5]
        return [
            {
                'id': str(c.id),
                'type': 'customer',
                'title': c.get_full_name(),
                'subtitle': f'{self._format_dominican_id(c.id_number)} - {c.email}' if c.email else self._format_dominican_id(c.id_number),
                'url': f'/customers/{c.id}',
            }
            for c in customers
        ]

    def _buscar_loans(self, query):
        from apps.loans.models import Loan
        loans = Loan.objects.filter(
            Q(loan_number__icontains=query) |
            Q(customer__first_name__icontains=query) |
            Q(customer__last_name__icontains=query)
        ).select_related('customer')[:5]
        return [
            {
                'id': str(loan.id),
                'type': 'loan',
                'title': f'Prestamo {loan.loan_number}',
                'subtitle': f'{loan.customer.get_full_name()} - {loan.get_status_display()}',
                'url': f'/loans/{loan.id}',
            }
            for loan in loans
        ]

    def _buscar_payments(self, query):
        from apps.loans.models import LoanPayment
        payments = LoanPayment.objects.filter(
            Q(reference_number__icontains=query) |
            Q(loan__loan_number__icontains=query) |
            Q(loan__customer__first_name__icontains=query) |
            Q(loan__customer__last_name__icontains=query)
        ).select_related('loan', 'loan__customer')[:5]
        return [
            {
                'id': str(payment.id),
                'type': 'payment',
                'title': f'Pago #{payment.payment_number}',
                'subtitle': f'{payment.loan.loan_number} - RD$ {payment.amount.amount:,.2f}',
                'url': f'/payments/{payment.id}',
            }
            for payment in payments
        ]

    def _buscar_contracts(self, query):
        # Los contratos viven en apps.loans (antes se importaba un apps.contracts inexistente
        # y la sección salía siempre vacía).
        from apps.loans.models_contracts import Contract
        contracts = Contract.objects.filter(
            Q(contract_number__icontains=query) |
            Q(loan__loan_number__icontains=query) |
            Q(loan__customer__first_name__icontains=query) |
            Q(loan__customer__last_name__icontains=query)
        ).select_related('loan', 'loan__customer')[:5]
        return [
            {
                'id': str(contract.id),
                'type': 'contract',
                'title': f'Contrato {contract.contract_number}',
                'subtitle': contract.loan.customer.get_full_name() if contract.loan else 'Sin prestamo',
                'url': f'/contracts/{contract.id}',
            }
            for contract in contracts
        ]
