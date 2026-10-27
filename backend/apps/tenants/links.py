"""Host y URLs (frontend y backend) de un tenant, siempre desde sus filas `Domain`.

Nunca se construyen con `schema_name` ni con `name`: el registro deriva el schema de `tenant_name` y
el dominio de `subdomain`, que pueden no coincidir (y un schema con `_` no es un host válido).
"""
import logging
from urllib.parse import urlparse

from django.conf import settings

logger = logging.getLogger(__name__)


def tenant_domain(tenant):
    """`domain` del `Domain` primario del tenant; si no hay primario, el primero por pk; si no, None."""
    domain = tenant.domains.filter(is_primary=True).first() or tenant.domains.order_by('pk').first()
    return domain.domain if domain else None


def _with_tenant_host(base_url, tenant, setting):
    """`base_url` con el host del dominio del tenant (scheme, puerto y ruta de `base_url`).

    Sin ningún `Domain`, devuelve `base_url` tal cual y deja un warning.
    """
    host = tenant_domain(tenant)
    if not host:
        logger.warning('El tenant %s no tiene dominio: el enlace usa %s sin host de tenant', tenant.pk, setting)
        return base_url
    parsed = urlparse(base_url)
    if parsed.port and ':' not in host:
        host = f'{host}:{parsed.port}'
    return parsed._replace(netloc=host).geturl()


def tenant_frontend_url(tenant):
    """URL del frontend del tenant: scheme, puerto y ruta de `FRONTEND_URL` con el host de su dominio.

    Sin ningún `Domain`, devuelve `FRONTEND_URL` tal cual y deja un warning.
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    return _with_tenant_host(frontend_url, tenant, 'FRONTEND_URL')


def tenant_backend_url(tenant):
    """URL del backend en el host del tenant: scheme y puerto de `BACKEND_URL` con el host de su dominio.

    Para rutas que sirve Django (p. ej. la confirmación de correo de allauth): django-tenants resuelve
    el tenant por el host, así que el enlace tiene que llevar el dominio del tenant. Sin ningún
    `Domain`, devuelve `BACKEND_URL` tal cual y deja un warning.
    """
    backend_url = getattr(settings, 'BACKEND_URL', 'http://localhost:8000')
    return _with_tenant_host(backend_url, tenant, 'BACKEND_URL')
