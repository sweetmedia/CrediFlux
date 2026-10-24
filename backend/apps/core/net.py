"""IP del cliente detrás de los proxies configurados.

Única fuente de verdad para "qué IP tiene el cliente": la usan el bloqueo de login,
el rate limit del login del admin, el throttle de registro y el audit log, con la
misma semántica que los throttles de DRF (`REST_FRAMEWORK['NUM_PROXIES']`,
variable de entorno `DRF_NUM_PROXIES`):

- `NUM_PROXIES` None o 0: `REMOTE_ADDR` (no se confía en `X-Forwarded-For`).
- `NUM_PROXIES` = N > 0: la N-ésima entrada de `X-Forwarded-For` contando desde la
  derecha (la que escribió el proxy más externo de confianza); lo que el cliente
  haya puesto más a la izquierda se ignora. Sin cabecera, `REMOTE_ADDR`.
"""
from rest_framework.settings import api_settings


def client_ip(request) -> str:
    if request is None:
        return ''
    meta = request.META
    remote_addr = (meta.get('REMOTE_ADDR') or '').strip()
    num_proxies = api_settings.NUM_PROXIES
    xff = meta.get('HTTP_X_FORWARDED_FOR')
    if not num_proxies or not xff:
        return remote_addr
    addrs = xff.split(',')
    client_addr = addrs[-min(num_proxies, len(addrs))].strip()
    return client_addr or remote_addr
