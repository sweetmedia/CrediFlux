"""
Utility functions for Django settings.
"""
from decouple import config


def environment_callback(request):
    """
    Callback function for Django Unfold to display environment badge.
    """
    environment = config('DJANGO_ENVIRONMENT', default='development')

    if environment == 'production':
        return ['Production','danger']
    elif environment == 'development':
        return ['Development','warning']
    else:
        return ['info', environment.title()]


def get_navigation(request):
    """
    Generate sidebar navigation dynamically based on the current schema.
    Returns different navigation items for public vs tenant schemas.
    """
    from django.db import connection
    from django.urls import reverse, NoReverseMatch

    def safe_reverse(viewname, default="#"):
        """Safely get reverse URL, return default if not found."""
        try:
            return reverse(viewname)
        except NoReverseMatch:
            return default

    # Get current schema
    schema_name = getattr(connection, 'schema_name', 'public')
    is_tenant = schema_name != 'public'

    # Base navigation - always visible
    navigation = [
        {
            "title": "Navigation",
            "separator": True,
            "items": [
                {
                    "title": "Dashboard",
                    "icon": "dashboard",
                    "link": safe_reverse("admin:index"),
                },
            ],
        },
    ]

    # Public schema navigation - Tenant Management first
    if not is_tenant:
        navigation.extend([
            {
                "title": "Tenant Management",
                "icon": "business",
                "items": [
                    {
                        "title": "Tenants",
                        "icon": "business_center",
                        "link": safe_reverse("admin:tenants_tenant_changelist"),
                    },
                    {
                        "title": "Domains",
                        "icon": "language",
                        "link": safe_reverse("admin:tenants_domain_changelist"),
                    },
                ],
            },
            {
                "title": "User Management",
                "icon": "group",
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": safe_reverse("admin:users_user_changelist"),
                    },
                    {
                        "title": "Groups",
                        "icon": "group_work",
                        "link": safe_reverse("admin:auth_group_changelist"),
                    },
                ],
            },
            {
                "title": "System",
                "separator": True,
                "items": [
                    {
                        "title": "Sites",
                        "icon": "public",
                        "link": safe_reverse("admin:sites_site_changelist"),
                    },
                    {
                        "title": "Auth Tokens",
                        "icon": "key",
                        "link": safe_reverse("admin:authtoken_tokenproxy_changelist"),
                    },
                ],
            },
        ])
    else:
        # Tenant schema navigation - Loan Management first
        navigation.extend([
            {
                "title": "Loan Management",
                "icon": "payments",
                "items": [
                    {
                        "title": "Customers",
                        "icon": "account_circle",
                        "link": safe_reverse("admin:loans_customer_changelist"),
                    },
                    {
                        "title": "Loans",
                        "icon": "account_balance",
                        "link": safe_reverse("admin:loans_loan_changelist"),
                    },
                    {
                        "title": "Loan Schedules",
                        "icon": "schedule",
                        "link": safe_reverse("admin:loans_loanschedule_changelist"),
                    },
                    {
                        "title": "Payments",
                        "icon": "payment",
                        "link": safe_reverse("admin:loans_loanpayment_changelist"),
                    },
                    {
                        "title": "Collaterals",
                        "icon": "shield",
                        "link": safe_reverse("admin:loans_collateral_changelist"),
                    },
                ],
            },
            {
                "title": "User Management",
                "icon": "group",
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": safe_reverse("admin:users_user_changelist"),
                    },
                    {
                        "title": "Groups",
                        "icon": "group_work",
                        "link": safe_reverse("admin:auth_group_changelist"),
                    },
                ],
            },
            {
                "title": "System",
                "separator": True,
                "items": [
                    {
                        "title": "Sites",
                        "icon": "public",
                        "link": safe_reverse("admin:sites_site_changelist"),
                    },
                    {
                        "title": "Auth Tokens",
                        "icon": "key",
                        "link": safe_reverse("admin:authtoken_tokenproxy_changelist"),
                    },
                ],
            },
        ])

    return navigation


def dashboard_callback(request, context):
    """
    Callback function for Django Unfold dashboard customization.
    Adds additional context variables for the dashboard template.
    """
    from django.db import connection
    from django.contrib.auth import get_user_model

    User = get_user_model()

    # Get current tenant info
    schema_name = getattr(connection, 'schema_name', 'public')
    is_tenant = schema_name != 'public'

    # Get tenant details if in tenant schema
    tenant_name = None
    tenant_logo = None
    if is_tenant:
        try:
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.get(schema_name=schema_name)
            tenant_name = tenant.business_name
            tenant_logo = tenant.logo.url if tenant.logo else None
        except Exception:
            tenant_name = schema_name.title()

    # Basic statistics
    context.update({
        'schema_name': schema_name,
        'is_tenant': is_tenant,
        'tenant_name': tenant_name,
        'tenant_logo': tenant_logo,
        'total_users': User.objects.count(),
    })

    # Tenant-specific stats
    if is_tenant:
        try:
            from apps.loans.models import Customer, Loan, LoanPayment

            context.update({
                'total_customers': Customer.objects.count(),
                'total_loans': Loan.objects.count(),
                'active_loans': Loan.objects.filter(status='active').count(),
                'total_payments': LoanPayment.objects.count(),
            })
        except Exception:
            pass
    else:
        # Public schema - add system-wide statistics
        try:
            from apps.tenants.models import Tenant
            from apps.loans.models import Customer, Loan, LoanPayment
            from django.core.cache import cache
            from constance import config as constance_config

            tenants = Tenant.objects.filter(is_active=True).order_by('name')

            # Build tenant list with domains
            tenants_list = []
            for tenant in tenants:
                domain = tenant.get_primary_domain()
                if domain:
                    tenants_list.append({
                        'name': tenant.name,
                        'business_name': tenant.business_name,
                        'schema_name': tenant.schema_name,
                        'domain': domain.domain,
                    })

            # Get aggregated statistics from all tenants
            total_customers_all = 0
            total_loans_all = 0
            total_active_loans = 0
            total_payments_all = 0

            for tenant in tenants:
                try:
                    connection.set_tenant(tenant)
                    total_customers_all += Customer.objects.count()
                    total_loans_all += Loan.objects.count()
                    total_active_loans += Loan.objects.filter(status='active').count()
                    total_payments_all += LoanPayment.objects.count()
                except Exception:
                    pass

            # Switch back to public schema
            connection.set_schema('public')

            # Check RNC database status
            rnc_cache_meta = cache.get('dgii_rnc_database_meta')
            rnc_status = {
                'enabled': constance_config.DGII_RNC_ENABLED,
                'total_records': rnc_cache_meta.get('total_records', 0) if rnc_cache_meta else 0,
                'last_updated': rnc_cache_meta.get('last_updated', 'Never') if rnc_cache_meta else 'Never',
            }

            context.update({
                'total_tenants': Tenant.objects.count(),
                'active_tenants': Tenant.objects.filter(is_active=True).count(),
                'tenants_list': tenants_list,
                # System-wide aggregated stats
                'total_customers_all': total_customers_all,
                'total_loans_all': total_loans_all,
                'total_active_loans': total_active_loans,
                'total_payments_all': total_payments_all,
                # System status
                'rnc_status': rnc_status,
            })
        except Exception as e:
            # Log the error but don't break the dashboard
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading dashboard context: {e}")
            pass

    return context


def get_sidebar_navigation():
    """
    Generate sidebar navigation structure for Unfold.
    Returns different navigation based on context (public vs tenant schema).
    """
    from django.urls import reverse_lazy
    from django.utils.translation import gettext_lazy as _

    # Base navigation structure that works for both schemas
    navigation = [
        {
            "title": _("Dashboard"),
            "separator": True,
            "items": [
                {
                    "title": _("Dashboard"),
                    "icon": "dashboard",
                    "link": reverse_lazy("admin:index"),
                },
            ],
        },
        {
            "title": _("Tenant Management"),
            "collapsible": False,
            "items": [
                {
                    "title": _("Tenants"),
                    "icon": "business_center",
                    "link": reverse_lazy("admin:tenants_tenant_changelist"),
                },
                {
                    "title": _("Domains"),
                    "icon": "language",
                    "link": reverse_lazy("admin:tenants_domain_changelist"),
                },
            ],
        },
        {
            "title": _("User Management"),
            "collapsible": False,
            "items": [
                {
                    "title": _("Users"),
                    "icon": "person",
                    "link": reverse_lazy("admin:users_user_changelist"),
                },
                {
                    "title": _("Groups"),
                    "icon": "group_work",
                    "link": reverse_lazy("admin:auth_group_changelist"),
                },
            ],
        },
        {
            "title": _("Loan Management"),
            "collapsible": False,
            "items": [
                {
                    "title": _("Customers"),
                    "icon": "account_circle",
                    "link": reverse_lazy("admin:loans_customer_changelist"),
                },
                {
                    "title": _("Loans"),
                    "icon": "account_balance",
                    "link": reverse_lazy("admin:loans_loan_changelist"),
                },
                {
                    "title": _("Loan Schedules"),
                    "icon": "schedule",
                    "link": reverse_lazy("admin:loans_loanschedule_changelist"),
                },
                {
                    "title": _("Loan Payments"),
                    "icon": "payment",
                    "link": reverse_lazy("admin:loans_loanpayment_changelist"),
                },
                {
                    "title": _("Collaterals"),
                    "icon": "shield",
                    "link": reverse_lazy("admin:loans_collateral_changelist"),
                },
            ],
        },
        {
            "title": _("Configuration"),
            "collapsible": False,
            "items": [
                {
                    "title": _("Settings"),
                    "icon": "settings",
                    "link": reverse_lazy("admin:constance_config_changelist"),
                },
            ],
        },
    ]

    return navigation
