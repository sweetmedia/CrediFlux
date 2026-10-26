"""IP del cliente detrás de los proxies configurados.

Única fuente de verdad para "qué IP tiene el cliente": la usan el bloqueo de login,
el rate limit del login del admin, el throttle de registro y el audit log, con la
misma semántica que los throttles de DRF (`REST_FRAMEWORK['NUM_PROXIES']`,
variable de entorno `DRF_NUM_PROXIES`):

- `NUM_PROXIES` None o 0: `REMOTE_ADDR` (no se confía en `X-Forwarded-For`).
- `NUM_PROXIES` = N > 0: la N-ésima entrada de `X-Forwarded-For` contando desde la
  derecha (la que escribió el proxy más externo de confianza); lo que el cliente
  haya puesto más a la izquierda se ignora. Sin cabecera, `REMOTE_ADDR`.

Para límites por cliente que no deben poder multiplicarse con direcciones baratas,
`client_network_key` agrupa IPv6 por su red /56 (throttle del registro). Los presupuestos
diarios del registro de tenants usan `client_registration_key`, que agrupa por /48.
"""
import hashlib
import ipaddress

from rest_framework.settings import api_settings

# Prefijo con el que se agrupa una IPv6 en una sola identidad de cliente.
IPV6_CLIENT_PREFIX = 56
# Y para los presupuestos de registro de tenants: una /48 es la delegación de un solo sitio.
IPV6_REGISTRATION_PREFIX = 48


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
    """Identidad del cliente para presupuestos por cliente: la IPv4 tal cual o su red IPv6 /56.

    Contar cada dirección IPv6 por separado regala a un solo host miles de millones de
    identidades, y agrupar por /64 (lo mínimo que se asigna a una LAN) tampoco basta: los
    proveedores suelen delegar a un solo cliente una /56 o /60, es decir 16-256 redes /64.
    La /56 es la delegación habitual de un cliente residencial. Una IPv4 mapeada en IPv6
    (`::ffff:a.b.c.d`) cuenta como esa IPv4 (si no, todas compartirían una /56). Un valor
    que no es una IP se devuelve tal cual.
    """
    return _network_key(client_ip(request), IPV6_CLIENT_PREFIX)


def client_registration_key(request) -> str:
    """Red de registro: la IPv4 tal cual o su red IPv6 /48 (la de `Tenant.registration_network`).

    Los presupuestos diarios del registro de tenants (altas y pendientes por red) no pueden
    multiplicarse con las 256 redes /56 de una sola /48, la delegación típica de un sitio:
    con /56 una /48 valía 256 registrantes y bastaba para llenar los topes globales.

    Un valor que no es una IP (p. ej. un X-Forwarded-For mal formado tras el proxy) se reduce
    a `raw:` + 32 hex de su SHA-256: cabe siempre en la columna (64) y el mismo valor sigue
    siendo la misma identidad, así que el presupuesto por cliente sigue contando.
    """
    ip = client_ip(request)
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        if not ip:
            return ''
        return 'raw:' + hashlib.sha256(ip.encode('utf-8', 'surrogatepass')).hexdigest()[:32]
    return _network_key(ip, IPV6_REGISTRATION_PREFIX)


def _network_key(ip, ipv6_prefix):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if addr.version == 6:
        if addr.ipv4_mapped is not None:
            return str(addr.ipv4_mapped)
        # int() descarta un posible identificador de zona (`%eth0`).
        return str(ipaddress.IPv6Network((int(addr), ipv6_prefix), strict=False))
    return str(addr)
