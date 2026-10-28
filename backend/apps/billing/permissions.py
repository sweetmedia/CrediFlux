"""
Permisos de facturación electrónica (e-CF) sobre el catálogo (D6).

Cada viewset declara su mapa `permission_codes` (acción → código `billing.*`) y lo exige con
`CanManageBilling`. La clase conserva su nombre histórico para los imports pero ya no mira el
rol: dueño y superusuario tienen todos los códigos; el resto, los de su Role. Lo que el mapa
no nombra se niega («Acción no configurada.») y el 403 por permiso lleva `required_permission`.
"""
from apps.users.authz import ViewPermissionRequired


class CanManageBilling(ViewPermissionRequired):
    """Facturación fiscal: certificados, secuencias e-NCF, facturas, proveedor e-CF y reportes."""
