"""
Core views
"""
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
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from apps.core.services.rnc_lookup import validate_rnc, is_rnc_database_loaded, RNCLookupService
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
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
        result = validate_rnc(rnc)

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
                'total_records': stats.get('total_records'),
                'last_updated': stats.get('last_updated'),
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
        "currency": "USD",
        "currency_symbol": "$",
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
                'currency': 'USD',
                'currency_symbol': '$',
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
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()

        if len(query) < 2:
            return Response({
                'query': query,
                'total_results': 0,
                'results': {
                    'customers': [],
                    'loans': [],
                    'payments': [],
                    'contracts': [],
                },
                'message': 'La busqueda debe tener al menos 2 caracteres'
            })

        results = {
            'customers': [],
            'loans': [],
            'payments': [],
            'contracts': [],
        }

        # Search Customers (tenant isolation handled by django-tenants schema)
        from apps.loans.models import Customer
        customers = Customer.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(id_number__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )[:5]

        results['customers'] = [
            {
                'id': str(c.id),
                'type': 'customer',
                'title': c.get_full_name(),
                'subtitle': f'{c.id_number} - {c.email}' if c.email else c.id_number,
                'url': f'/customers/{c.id}',
            }
            for c in customers
        ]

        # Search Loans
        from apps.loans.models import Loan
        loans = Loan.objects.filter(
            Q(loan_number__icontains=query) |
            Q(customer__first_name__icontains=query) |
            Q(customer__last_name__icontains=query)
        ).select_related('customer')[:5]

        results['loans'] = [
            {
                'id': str(loan.id),
                'type': 'loan',
                'title': f'Prestamo {loan.loan_number}',
                'subtitle': f'{loan.customer.get_full_name()} - {loan.get_status_display()}',
                'url': f'/loans/{loan.id}',
            }
            for loan in loans
        ]

        # Search Payments
        from apps.loans.models import LoanPayment
        payments = LoanPayment.objects.filter(
            Q(receipt_number__icontains=query) |
            Q(loan__loan_number__icontains=query) |
            Q(loan__customer__first_name__icontains=query) |
            Q(loan__customer__last_name__icontains=query)
        ).select_related('loan', 'loan__customer')[:5]

        results['payments'] = [
            {
                'id': str(payment.id),
                'type': 'payment',
                'title': f'Pago {payment.receipt_number or payment.id}',
                'subtitle': f'{payment.loan.loan_number} - ${payment.amount}',
                'url': f'/payments/{payment.id}',
            }
            for payment in payments
        ]

        # Search Contracts (if app exists)
        try:
            from apps.contracts.models import Contract
            contracts = Contract.objects.filter(
                Q(contract_number__icontains=query) |
                Q(loan__loan_number__icontains=query) |
                Q(loan__customer__first_name__icontains=query) |
                Q(loan__customer__last_name__icontains=query)
            ).select_related('loan', 'loan__customer')[:5]

            results['contracts'] = [
                {
                    'id': str(contract.id),
                    'type': 'contract',
                    'title': f'Contrato {contract.contract_number}',
                    'subtitle': contract.loan.customer.get_full_name() if contract.loan else 'Sin prestamo',
                    'url': f'/contracts/{contract.id}',
                }
                for contract in contracts
            ]
        except (ImportError, Exception):
            pass

        # Calculate total results
        total_results = sum(len(v) for v in results.values())

        return Response({
            'query': query,
            'total_results': total_results,
            'results': results,
        })
