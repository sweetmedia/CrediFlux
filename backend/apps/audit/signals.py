from django.db import connection, transaction
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import AuditLog
from .middleware import get_current_request, get_client_ip, get_user_agent

User = get_user_model()

# Models to track for audit logging
TRACKED_MODELS = {
    'apps.loans.models.Loan': 'Loan',
    'apps.loans.models.LoanPayment': 'LoanPayment',
    'apps.loans.models.Customer': 'Customer',
    'apps.loans.models.Collateral': 'Collateral',
    'apps.loans.models_contracts.Contract': 'Contract',
    'apps.users.models.User': 'User',
    'apps.tenants.models.Tenant': 'Tenant',
    'apps.cashbox.models.CashSession': 'CashSession',
    'apps.cashbox.models.CashMovement': 'CashMovement',
    'apps.billing.models.Invoice': 'Invoice',
    'apps.billing.models.FiscalSequence': 'FiscalSequence',
    'apps.billing.models.DigitalCertificate': 'DigitalCertificate',
}

# Fields to exclude from change tracking (never written to AuditLog.changes)
EXCLUDED_FIELDS = {
    'password', 'totp_secret', 'backup_codes', 'last_login',
    'modified_at', 'updated_at', 'created_at',
    # Secretos del Tenant / facturación
    'smtp_password', 'imap_password',
    'whatsapp_access_token', 'whatsapp_token', 'whatsapp_app_secret', 'whatsapp_verify_token',
    'ai_api_key', 'nexconnect_api_key', 'nexconnect_webhook_secret',
    'ecf_provider_api_key', 'ecf_provider_api_secret',
    'stripe_secret_key', 'paypal_client_secret',
    'certificate_password',
    # Blobs de e-CF (decenas de KB por actualización DGII; no aportan al log)
    'xml_content', 'signed_xml', 'dgii_response',
}

# Cualquier campo cuyo nombre contenga uno de estos fragmentos se trata como secreto.
SENSITIVE_NAME_FRAGMENTS = ('password', 'secret', 'token', 'api_key')


def is_sensitive_field(field_name):
    """True si el nombre del campo sugiere un secreto (password, secret, token, api_key)."""
    name = field_name.lower()
    return any(fragment in name for fragment in SENSITIVE_NAME_FRAGMENTS)


def is_excluded_field(field_name):
    return field_name in EXCLUDED_FIELDS or is_sensitive_field(field_name)


def get_model_key(instance):
    """Get the full model path for an instance."""
    model = instance.__class__
    return f'{model.__module__}.{model.__name__}'


def should_track_model(instance):
    """Check if the model should be tracked."""
    model_key = get_model_key(instance)
    # Check exact match or simplified match
    if model_key in TRACKED_MODELS:
        return True
    # Also check simplified path
    model_name = instance.__class__.__name__
    for key in TRACKED_MODELS:
        if key.endswith(f'.{model_name}'):
            return True
    return False


def _real_tenant(candidate):
    """Devuelve `candidate` sólo si es un Tenant persistido (no el FakeTenant de django-tenants)."""
    from apps.tenants.models import Tenant

    if isinstance(candidate, Tenant) and candidate.pk:
        return candidate
    return None


def get_tenant_for_instance(instance):
    """
    Tenant al que pertenece el registro auditado.

    1. FK `tenant` en la instancia (o la instancia ES un Tenant).
    2. `connection.tenant` si el schema activo no es el público: el registro vive
       en ese schema aunque el request venga de otro host (p. ej. un webhook del
       host público que guarda bajo `schema_context(B)`).
    3. `request.tenant` del request en curso.
    Devuelve None sólo si nada de lo anterior existe.
    """
    if instance.__class__.__name__ == 'Tenant':
        return instance
    if getattr(instance, 'tenant_id', None):
        try:
            tenant = _real_tenant(instance.tenant)
        except Exception:
            tenant = None
        if tenant:
            return tenant

    from django_tenants.utils import get_public_schema_name

    schema_name = getattr(connection, 'schema_name', None)
    if schema_name not in (None, get_public_schema_name()):
        tenant = _real_tenant(getattr(connection, 'tenant', None))
        if tenant is None:
            # schema_context()/set_schema() dejan un FakeTenant: buscar el real
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.filter(schema_name=schema_name).first()
        if tenant:
            return tenant

    request = get_current_request()
    return _real_tenant(getattr(request, 'tenant', None)) if request else None


def get_field_value(instance, field_name):
    """Safely get a field value, handling related fields."""
    try:
        value = getattr(instance, field_name, None)
        # Handle foreign keys
        if hasattr(value, 'pk'):
            return str(value.pk)
        # Handle datetime/date fields
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        # Handle decimal
        if hasattr(value, 'as_tuple'):
            return str(value)
        # Handle None
        if value is None:
            return None
        return str(value)
    except Exception:
        return None


def get_changes(old_instance, new_instance):
    """Compare two instances and return the changes."""
    changes = {}

    if old_instance is None:
        return changes

    # Get all field names
    for field in new_instance._meta.fields:
        field_name = field.name

        # Skip excluded / secret fields (ni old ni new llegan al log)
        if is_excluded_field(field_name):
            continue

        old_value = get_field_value(old_instance, field_name)
        new_value = get_field_value(new_instance, field_name)

        if old_value != new_value:
            changes[field_name] = {
                'old': old_value,
                'new': new_value
            }

    return changes


@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    """
    Capture the state of the instance before save.
    This allows us to compare old vs new values.

    El snapshot vive en la propia instancia (`_audit_old_instance`) y
    `audit_post_save` lo consume; no hay estado de módulo que crezca.
    """
    if not should_track_model(instance):
        return

    # Only capture if this is an update (has pk) and the log can be attributed
    if not instance.pk or get_tenant_for_instance(instance) is None:
        return
    try:
        # No cargar los campos que nunca se comparan (secretos y blobs XML)
        deferred = [
            f.attname for f in sender._meta.concrete_fields
            if not f.primary_key and is_excluded_field(f.name)
        ]
        instance._audit_old_instance = (
            sender._default_manager.defer(*deferred).get(pk=instance.pk)
        )
    except sender.DoesNotExist:
        pass


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """Log create and update actions."""
    # Consumir el snapshot antes de cualquier return para no dejarlo colgado
    old_instance = instance.__dict__.pop('_audit_old_instance', None)

    if not should_track_model(instance):
        return

    # Skip AuditLog itself to prevent infinite loop
    if sender.__name__ == 'AuditLog':
        return

    tenant = get_tenant_for_instance(instance)
    if not tenant:
        return

    request = get_current_request()
    user = getattr(request, 'user', None) if request else None
    ip_address = get_client_ip(request) if request else None
    user_agent = get_user_agent(request) if request else None

    # Determine action and get changes
    action = 'create' if created else 'update'
    changes = {}

    if not created:
        changes = get_changes(old_instance, instance)

        # Skip if no meaningful changes
        if not changes:
            return

    # Create audit log
    try:
        # Savepoint: si el INSERT falla, la transacción del caller sigue usable
        with transaction.atomic():
            AuditLog.objects.create(
                tenant=tenant,
                user=user if user and user.is_authenticated else None,
                user_email=user.email if user and user.is_authenticated else 'system@crediflux.app',
                action=action,
                model_name=sender.__name__,
                object_id=str(instance.pk),
                object_repr=str(instance)[:255],
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
            )
    except Exception as e:
        # Don't let audit logging failures break the application
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Failed to create audit log: {e}')


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    """Log delete actions."""
    if not should_track_model(instance):
        return

    # Skip AuditLog itself
    if sender.__name__ == 'AuditLog':
        return

    tenant = get_tenant_for_instance(instance)
    if not tenant:
        return

    request = get_current_request()
    user = getattr(request, 'user', None) if request else None
    ip_address = get_client_ip(request) if request else None
    user_agent = get_user_agent(request) if request else None

    try:
        # Savepoint: si el INSERT falla, la transacción del caller sigue usable
        with transaction.atomic():
            AuditLog.objects.create(
                tenant=tenant,
                user=user if user and user.is_authenticated else None,
                user_email=user.email if user and user.is_authenticated else 'system@crediflux.app',
                action='delete',
                model_name=sender.__name__,
                object_id=str(instance.pk),
                object_repr=str(instance)[:255],
                changes={},
                ip_address=ip_address,
                user_agent=user_agent,
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Failed to create audit log: {e}')
