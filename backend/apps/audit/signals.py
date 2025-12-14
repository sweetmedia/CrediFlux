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
    'apps.contracts.models.Contract': 'Contract',
    'apps.users.models.User': 'User',
    'apps.tenants.models.Tenant': 'Tenant',
}

# Fields to exclude from change tracking
EXCLUDED_FIELDS = {
    'password', 'totp_secret', 'backup_codes', 'last_login',
    'modified_at', 'updated_at', 'created_at',
}


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


def get_tenant_for_instance(instance):
    """Get the tenant for an instance."""
    # Check if instance has a tenant attribute
    if hasattr(instance, 'tenant') and instance.tenant:
        return instance.tenant
    # Check if instance IS a tenant
    if instance.__class__.__name__ == 'Tenant':
        return instance
    # Check if instance is a User with a tenant
    if hasattr(instance, 'tenant_id'):
        from apps.tenants.models import Tenant
        try:
            return Tenant.objects.get(pk=instance.tenant_id)
        except Tenant.DoesNotExist:
            pass
    return None


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

        # Skip excluded fields
        if field_name in EXCLUDED_FIELDS:
            continue

        old_value = get_field_value(old_instance, field_name)
        new_value = get_field_value(new_instance, field_name)

        if old_value != new_value:
            changes[field_name] = {
                'old': old_value,
                'new': new_value
            }

    return changes


# Store for pre_save values
_pre_save_instances = {}


@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    """
    Capture the state of the instance before save.
    This allows us to compare old vs new values.
    """
    if not should_track_model(instance):
        return

    # Only capture if this is an update (has pk)
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            # Store in thread-local-like dict keyed by model+pk
            key = f'{sender.__name__}_{instance.pk}'
            _pre_save_instances[key] = old_instance
        except sender.DoesNotExist:
            pass


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """Log create and update actions."""
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
        key = f'{sender.__name__}_{instance.pk}'
        old_instance = _pre_save_instances.pop(key, None)
        changes = get_changes(old_instance, instance)

        # Skip if no meaningful changes
        if not changes:
            return

    # Create audit log
    try:
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
