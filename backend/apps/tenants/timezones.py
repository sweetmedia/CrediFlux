"""
Zona horaria por tenant.

- En requests, `TenantTimezoneMiddleware` activa la zona del tenant: dentro de
  una vista, `django.utils.timezone.localdate()` es el "hoy" de la financiera.
- Fuera de un request (Celery, comandos), envuelve el trabajo de cada tenant en
  `use_tenant_timezone(tenant)`.

Regla: para "hoy" usa siempre `timezone.localdate()`, nunca
`timezone.now().date()` (es la fecha UTC) ni `date.today()` (la del servidor).
"""
from contextlib import contextmanager
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone


def tenant_zone(tenant):
    """ZoneInfo del tenant (la de settings.TIME_ZONE si no tiene o es inválida)."""
    name = getattr(tenant, 'timezone', None) or settings.TIME_ZONE
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(settings.TIME_ZONE)


def tenant_now(tenant):
    """Fecha y hora actuales en la zona del tenant."""
    return timezone.now().astimezone(tenant_zone(tenant))


@contextmanager
def use_tenant_timezone(tenant):
    """Activa la zona del tenant mientras dura el bloque."""
    with timezone.override(tenant_zone(tenant)):
        yield
