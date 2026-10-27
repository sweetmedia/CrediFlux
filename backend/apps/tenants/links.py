"""Host y URL del frontend de un tenant, siempre desde sus filas `Domain`.

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


def tenant_frontend_url(tenant):
    """URL del frontend del tenant: scheme, puerto y ruta de `FRONTEND_URL` con el host de su dominio.

    Sin ningún `Domain`, devuelve `FRONTEND_URL` tal cual y deja un warning.
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    host = tenant_domain(tenant)
    if not host:
        logger.warning('El tenant %s no tiene dominio: el enlace usa FRONTEND_URL sin host de tenant', tenant.pk)
        return frontend_url
    parsed = urlparse(frontend_url)
    if parsed.port and ':' not in host:
        host = f'{host}:{parsed.port}'
    return parsed._replace(netloc=host).geturl()
