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
    Following Unfold best practices: https://unfoldadmin.com/docs/configuration/dashboard
    """
    from decimal import Decimal
    from django.db import connection
    from django.contrib.auth import get_user_model
    from django.templatetags.static import static

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

    # System logo for non-tenant (public) dashboard
    system_logo = static('admin/img/logo.svg') if not is_tenant else None

    # Basic statistics
    context.update({
        'schema_name': schema_name,
        'is_tenant': is_tenant,
        'tenant_name': tenant_name,
        'tenant_logo': tenant_logo,
        'system_logo': system_logo,  # Add system logo to context
        'total_users': User.objects.count(),
    })

    def money_amount(value):
        """Safely normalize Money/Decimal/None values to Decimal."""
        if value is None:
            return Decimal('0')
        amount = getattr(value, 'amount', value)
        try:
            return Decimal(str(amount))
        except Exception:
            return Decimal('0')

    # Tenant-specific stats
    if is_tenant:
        try:
            from apps.loans.models import Customer, Loan, LoanPayment, Contract

            loans = Loan.objects.all()
            total_outstanding = Decimal('0')
            total_principal = Decimal('0')
            overdue_loans = 0

            for loan in loans:
                total_outstanding += money_amount(loan.outstanding_balance)
                total_principal += money_amount(loan.principal_amount)
                try:
                    if loan.is_overdue:
                        overdue_loans += 1
                except Exception:
                    pass

            context.update({
                'total_customers': Customer.objects.count(),
                'total_loans': loans.count(),
                'active_loans': loans.filter(status='active').count(),
                'total_payments': LoanPayment.objects.count(),
                'overdue_loans': overdue_loans,
                'total_outstanding': total_outstanding,
                'total_principal': total_principal,
                'pending_contract_signatures': Contract.objects.filter(status='sent').count(),
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
            total_outstanding_all = Decimal('0')
            total_principal_all = Decimal('0')
            total_overdue_loans_all = 0

            tenants_summary = []
            plan_counts = {
                'basic': 0,
                'professional': 0,
                'enterprise': 0,
            }
            feature_adoption = {
                'email': 0,
                'whatsapp': 0,
                'ecf': 0,
                'ai': 0,
            }

            for tenant in tenants:
                try:
                    plan_counts[tenant.subscription_plan] = plan_counts.get(tenant.subscription_plan, 0) + 1
                    if tenant.enable_email_reminders:
                        feature_adoption['email'] += 1
                    if tenant.enable_whatsapp_reminders:
                        feature_adoption['whatsapp'] += 1
                    if tenant.ecf_provider and tenant.ecf_provider != 'none':
                        feature_adoption['ecf'] += 1
                    if tenant.enable_ai_assistant:
                        feature_adoption['ai'] += 1

                    connection.set_tenant(tenant)
                    tenant_customers = Customer.objects.count()
                    tenant_loans = Loan.objects.count()
                    tenant_active_loans = Loan.objects.filter(status='active').count()
                    tenant_payments = LoanPayment.objects.count()

                    tenant_outstanding = Decimal('0')
                    tenant_principal = Decimal('0')
                    tenant_overdue_loans = 0
                    for loan in Loan.objects.all():
                        tenant_outstanding += money_amount(loan.outstanding_balance)
                        tenant_principal += money_amount(loan.principal_amount)
                        try:
                            if loan.is_overdue:
                                tenant_overdue_loans += 1
                        except Exception:
                            pass

                    total_customers_all += tenant_customers
                    total_loans_all += tenant_loans
                    total_active_loans += tenant_active_loans
                    total_payments_all += LoanPayment.objects.count()
                    total_outstanding_all += tenant_outstanding
                    total_principal_all += tenant_principal
                    total_overdue_loans_all += tenant_overdue_loans

                    primary_domain = tenant.get_primary_domain()
                    admin_url = None
                    if primary_domain:
                        admin_url = f"https://{primary_domain.domain}/admin/"

                    tenants_summary.append({
                        'name': tenant.name,
                        'business_name': tenant.business_name,
                        'schema_name': tenant.schema_name,
                        'subscription_plan': tenant.get_subscription_plan_display(),
                        'customers': tenant_customers,
                        'loans': tenant_loans,
                        'active_loans': tenant_active_loans,
                        'payments': tenant_payments,
                        'outstanding_balance': tenant_outstanding,
                        'principal_disbursed': tenant_principal,
                        'overdue_loans': tenant_overdue_loans,
                        'admin_url': admin_url,
                    })
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
                'tenants_summary': sorted(
                    tenants_summary,
                    key=lambda item: (item['outstanding_balance'], item['loans']),
                    reverse=True,
                ),
                # System-wide aggregated stats
                'total_customers_all': total_customers_all,
                'total_loans_all': total_loans_all,
                'total_active_loans': total_active_loans,
                'total_payments_all': total_payments_all,
                'total_outstanding_all': total_outstanding_all,
                'total_principal_all': total_principal_all,
                'total_overdue_loans_all': total_overdue_loans_all,
                'plan_counts': plan_counts,
                'feature_adoption': feature_adoption,
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
    Static fallback: Returns full navigation for both schemas.
    Used only if the dynamic callback is not configured.
    """
    from django.urls import reverse_lazy
    from django.utils.translation import gettext_lazy as _

    return _build_full_navigation()


def get_sidebar_navigation_callback(request):
    """
    Dynamic sidebar navigation callback for Unfold.
    Returns different navigation based on current schema (public vs tenant).
    This is called per-request so it can adapt to the current context.
    """
    from django.db import connection
    from django.urls import reverse_lazy, NoReverseMatch
    from django.utils.translation import gettext_lazy as _

    def safe_reverse(viewname):
        try:
            return reverse_lazy(viewname)
        except NoReverseMatch:
            return '#'

    schema_name = getattr(connection, 'schema_name', 'public')
    is_tenant = schema_name != 'public'

    # Common: Dashboard
    navigation = [
        {
            "title": _("Inicio"),
            "separator": True,
            "items": [
                {
                    "title": _("Dashboard"),
                    "icon": "dashboard",
                    "link": safe_reverse("admin:index"),
                },
            ],
        },
    ]

    if is_tenant:
        # ========== TENANT SCHEMA ==========
        # Show loan management first (primary use case)
        navigation.extend([
            {
                "title": _("Operación crediticia"),
                "collapsible": False,
                "items": [
                    {
                        "title": _("Clientes"),
                        "icon": "account_circle",
                        "link": safe_reverse("admin:loans_customer_changelist"),
                    },
                    {
                        "title": _("Préstamos"),
                        "icon": "account_balance",
                        "link": safe_reverse("admin:loans_loan_changelist"),
                    },
                    {
                        "title": _("Calendario de pagos"),
                        "icon": "schedule",
                        "link": safe_reverse("admin:loans_loanschedule_changelist"),
                    },
                    {
                        "title": _("Pagos"),
                        "icon": "payment",
                        "link": safe_reverse("admin:loans_loanpayment_changelist"),
                    },
                    {
                        "title": _("Garantías"),
                        "icon": "shield",
                        "link": safe_reverse("admin:loans_collateral_changelist"),
                    },
                    {
                        "title": _("Garantes"),
                        "icon": "groups",
                        "link": safe_reverse("admin:loans_guarantor_changelist"),
                    },
                ],
            },
            {
                "title": _("Cobros y contratos"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Recordatorios"),
                        "icon": "notifications",
                        "link": safe_reverse("admin:loans_collectionreminder_changelist"),
                    },
                    {
                        "title": _("Historial de contacto"),
                        "icon": "phone_in_talk",
                        "link": safe_reverse("admin:loans_collectioncontact_changelist"),
                    },
                    {
                        "title": _("Contratos"),
                        "icon": "description",
                        "link": safe_reverse("admin:loans_contract_changelist"),
                    },
                    {
                        "title": _("Plantillas"),
                        "icon": "article",
                        "link": safe_reverse("admin:loans_contracttemplate_changelist"),
                    },
                ],
            },
            {
                "title": _("Facturación y comunicación"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Facturas"),
                        "icon": "receipt_long",
                        "link": safe_reverse("admin:billing_invoice_changelist"),
                    },
                    {
                        "title": _("Envíos e-CF"),
                        "icon": "send",
                        "link": safe_reverse("admin:billing_ecfsubmission_changelist"),
                    },
                    {
                        "title": _("Emails"),
                        "icon": "mail",
                        "link": safe_reverse("admin:communications_email_changelist"),
                    },
                    {
                        "title": _("WhatsApp"),
                        "icon": "chat",
                        "link": safe_reverse("admin:communications_whatsappmessage_changelist"),
                    },
                ],
            },
            {
                "title": _("Equipo y seguridad"),
                "collapsible": False,
                "items": [
                    {
                        "title": _("Usuarios"),
                        "icon": "person",
                        "link": safe_reverse("admin:users_user_changelist"),
                    },
                    {
                        "title": _("Grupos"),
                        "icon": "group_work",
                        "link": safe_reverse("admin:auth_group_changelist"),
                    },
                    {
                        "title": _("Auditoría"),
                        "icon": "history",
                        "link": safe_reverse("admin:audit_auditlog_changelist"),
                    },
                ],
            },
        ])
    else:
        # ========== PUBLIC SCHEMA (System Admin) ==========
        # Show tenant management first
        navigation.extend([
            {
                "title": _("SaaS y tenants"),
                "collapsible": False,
                "items": [
                    {
                        "title": _("Tenants"),
                        "icon": "business_center",
                        "link": safe_reverse("admin:tenants_tenant_changelist"),
                    },
                    {
                        "title": _("Dominios"),
                        "icon": "language",
                        "link": safe_reverse("admin:tenants_domain_changelist"),
                    },
                ],
            },
            {
                "title": _("Plataforma"),
                "collapsible": False,
                "items": [
                    {
                        "title": _("Usuarios"),
                        "icon": "person",
                        "link": safe_reverse("admin:users_user_changelist"),
                    },
                    {
                        "title": _("Grupos"),
                        "icon": "group_work",
                        "link": safe_reverse("admin:auth_group_changelist"),
                    },
                    {
                        "title": _("Auditoría"),
                        "icon": "history",
                        "link": safe_reverse("admin:audit_auditlog_changelist"),
                    },
                ],
            },
            {
                "title": _("Operación técnica"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Tareas programadas"),
                        "icon": "timer",
                        "link": safe_reverse("admin:django_celery_beat_periodictask_changelist"),
                    },
                    {
                        "title": _("Certificados digitales"),
                        "icon": "verified",
                        "link": safe_reverse("admin:billing_digitalcertificate_changelist"),
                    },
                    {
                        "title": _("Secuencias fiscales"),
                        "icon": "tag",
                        "link": safe_reverse("admin:billing_fiscalsequence_changelist"),
                    },
                ],
            },
        ])
    
    # Common: Configuration (both schemas)
    navigation.append({
        "title": _("Configuración"),
        "collapsible": False,
        "items": [
            {
                "title": _("Settings"),
                "icon": "settings",
                "link": safe_reverse("admin:constance_config_changelist"),
            },
        ],
    })

    return navigation


def _build_full_navigation():
    """Build full navigation with all items (static fallback)."""
    from django.urls import reverse_lazy
    from django.utils.translation import gettext_lazy as _

    return [
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


def get_tenant_dropdown(request):
    """
    Generate dropdown menu for tenant navigation.
    Shows all active tenants ONLY to superusers and public schema staff.
    Regular tenant users see no dropdown (they can only access their tenant).

    Dynamically builds URLs based on the incoming request so it works in
    both local dev (*.localhost:8000) and production (*.crediflux.com.do).
    """
    from django.db import connection
    from django.utils.translation import gettext_lazy as _

    dropdown = []

    # Only show dropdown to authenticated users
    if not request.user.is_authenticated:
        return dropdown

    try:
        from apps.tenants.models import Tenant, Domain

        # Get current schema
        current_schema = getattr(connection, 'schema_name', 'public')

        # Check if user should see the dropdown
        is_superuser = request.user.is_superuser
        is_public_staff = request.user.has_perm('tenants.view_tenant')

        # Regular tenant users should not see the dropdown
        if not (is_superuser or is_public_staff):
            return dropdown

        # Detect scheme + base domain from request
        host = request.get_host()          # e.g. "app.crediflux.com.do" or "demo.localhost:8000"
        scheme = 'https' if request.is_secure() else 'http'

        # Figure out the "base" domain so we can build sibling URLs.
        # Production: app.crediflux.com.do → crediflux.com.do
        # Local:      demo.localhost:8000  → localhost:8000
        parts = host.split('.')
        if 'localhost' in host:
            # Local dev: keep localhost:PORT
            base_domain = 'localhost' + (':' + host.split(':')[1] if ':' in host else '')
        elif len(parts) >= 3:
            # subdomain.domain.tld → domain.tld
            base_domain = '.'.join(parts[-2:])
        else:
            base_domain = host

        # System Dashboard — public schema tenant
        # Find the primary domain for the public tenant
        try:
            public_tenant = Tenant.objects.get(schema_name='public')
            public_domain = Domain.objects.filter(tenant=public_tenant, is_primary=True).first()
            if public_domain:
                system_host = public_domain.domain
            else:
                system_host = f"app.{base_domain}" if 'localhost' not in host else f"localhost:{host.split(':')[1]}" if ':' in host else 'localhost'
        except Tenant.DoesNotExist:
            system_host = host

        dropdown.append({
            "icon": "settings_suggest",
            "title": _("System Dashboard"),
            "link": f"{scheme}://{system_host}/admin/",
        })

        # Get all active tenants (excluding public)
        tenants = Tenant.objects.filter(is_active=True).exclude(schema_name='public').order_by('name')

        for tenant in tenants:
            # Prefer the tenant's primary domain if it exists
            primary_domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
            if primary_domain:
                tenant_host = primary_domain.domain
            else:
                # Fallback: build subdomain URL
                if 'localhost' in host:
                    port = ':' + host.split(':')[1] if ':' in host else ''
                    tenant_host = f"{tenant.schema_name}.localhost{port}"
                else:
                    tenant_host = f"{tenant.schema_name}.{base_domain}"

            dropdown.append({
                "icon": "business",
                "title": tenant.business_name or tenant.name,
                "link": f"{scheme}://{tenant_host}/admin/",
            })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating tenant dropdown: {e}")
        pass

    return dropdown
