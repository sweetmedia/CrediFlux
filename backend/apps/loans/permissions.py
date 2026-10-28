"""
Permisos de préstamos, clientes, pagos y cobranza sobre el catálogo (D6).

Cada viewset declara su mapa completo `permission_codes` (acción → código del catálogo,
apps/users/permissions_catalog.py) y lo exige con una de las clases de abajo. Las clases
conservan sus nombres históricos para que los imports sigan valiendo, pero ya no miran el rol:
el código sale del mapa de la vista y se resuelve con `has_perm` (superusuario y dueño, todos).
Lo que el mapa no nombra se niega («Acción no configurada.», R12); el 403 por permiso lleva
`required_permission`.
"""
from apps.users.authz import ViewPermissionRequired, has_perm


class CanManageLoans(ViewPermissionRequired):
    """Clientes, documentos, préstamos, garantías, garantes y contratos: `view.permission_codes`."""


class CanRegisterPayments(ViewPermissionRequired):
    """Pagos: `view.permission_codes` (LoanPaymentViewSet)."""


class CanManageCollections(ViewPermissionRequired):
    """Cobranza (recordatorios, contactos, teléfonos, correos, visitas y GPS): `view.permission_codes`."""


def can_manage_loans(user, code='loans.edit'):
    """¿Tiene el usuario `code`? Lo usa el admin de Django para escribir préstamos, garantías,
    garantes (`loans.create` / `loans.edit`) y contratos (`contracts.create`), en paridad con la API.
    """
    if not user or not user.is_authenticated:
        return False
    return has_perm(user, code)
