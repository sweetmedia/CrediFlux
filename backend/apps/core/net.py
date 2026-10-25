"""IP del cliente detrás de los proxies configurados.

Única fuente de verdad para "qué IP tiene el cliente": la usan el bloqueo de login,
el rate limit del login del admin, el throttle de registro y el audit log, con la
misma semántica que los throttles de DRF (`REST_FRAMEWORK['NUM_PROXIES']`,
variable de entorno `DRF_NUM_PROXIES`):

- `NUM_PROXIES` None o 0: `REMOTE_ADDR` (no se confía en `X-Forwarded-For`).
- `NUM_PROXIES` = N > 0: la N-ésima entrada de `X-Forwarded-For` contando desde la
  derecha (la que escribió el proxy más externo de confianza); lo que el cliente
  haya puesto más a la izquierda se ignora. Sin cabecera, `REMOTE_ADDR`.

Para presupuestos por cliente que no deben poder multiplicarse con direcciones baratas
(registro de tenants), `client_network_key` agrupa IPv6 por su red /64.
"""
import ipaddress

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


def client_network_key(request) -> str:
    """Identidad del cliente para presupuestos por cliente: la IPv4 tal cual o su red IPv6 /64.

    Una /64 es lo mínimo que se asigna a un host o una LAN IPv6: contar cada dirección por
    separado regala a un solo host miles de millones de identidades. Una IPv4 mapeada en
    IPv6 (`::ffff:a.b.c.d`) cuenta como esa IPv4 (si no, todas compartirían una /64). Un
    valor que no es una IP se devuelve tal cual.
    """
    ip = client_ip(request)
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if addr.version == 6:
        if addr.ipv4_mapped is not None:
            return str(addr.ipv4_mapped)
        # int() descarta un posible identificador de zona (`%eth0`).
        return str(ipaddress.IPv6Network((int(addr), 64), strict=False))
    return str(addr)
