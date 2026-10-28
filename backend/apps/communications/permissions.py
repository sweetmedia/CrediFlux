"""
Permisos de comunicaciones sobre el catálogo (D6).

Cada viewset declara su mapa `permission_codes` (acción → código `comms.*`). Las clases
conservan sus nombres históricos para los imports pero ya no miran el rol: dueño y superusuario
tienen todos los códigos; el resto, los de su Role. Lo que el mapa no nombra se niega
(«Acción no configurada.») y el 403 por permiso lleva `required_permission`.
"""
from apps.users.authz import ViewPermissionRequired


class CanSendMessages(ViewPermissionRequired):
    """Enviar mensajes a clientes (WhatsApp): `comms.whatsapp` en `view.permission_codes`."""


class CanManageTasks(ViewPermissionRequired):
    """Tablero de tareas: leer con `comms.view`, escribir con `comms.tasks`."""
