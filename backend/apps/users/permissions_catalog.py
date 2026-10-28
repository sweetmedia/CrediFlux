"""Catálogo de permisos de los roles editables por financiera (D6).

`MODULES` lista los 47 códigos del prototipo aprobado (`design-prototypes/settings-roles.html`,
pantalla Configuración › Roles) en su orden, más tres que cubren chequeos que ya existen:
`collections.supervise` (ver las visitas y ubicaciones de todos los cobradores,
`loans/views_geolocation.py:23`), `cashbox.registers` (borrar cajas, `cashbox/views.py:65`) y
`billing.config` (proveedor e-CF, `billing/views.py:425`).

`DEFAULT_ROLE_PERMISSIONS` son los permisos con que nacen los 8 roles de sistema. Se derivan de
la matriz de autorización de hoy (`tests/authz_cases.py`: `CODE` + `EXPECTED`) para que pasar de
roles fijos a permisos no cambie lo que cada rol puede hacer; lo verifica
`apps/users/tests/test_roles_model.py`. Quedan fuera del catálogo, como reglas aparte: el
reverso de pagos (dueño/superusuario), dar el rol admin (dueño/superusuario), la exención
maker-checker del desembolso (admin/dueño) y el bypass del dueño y del superusuario.
"""

MODULES = [
    ('customers', 'Clientes', [
        ('customers.view', 'Ver clientes'),
        ('customers.create', 'Crear clientes'),
        ('customers.edit', 'Editar clientes'),
        ('customers.delete', 'Eliminar clientes'),
        ('customers.documents.view', 'Ver documentos'),
        ('customers.documents.verify', 'Verificar documentos'),
        ('customers.statement', 'Generar estado de cuenta'),
    ]),
    ('loans', 'Préstamos', [
        ('loans.view', 'Ver préstamos'),
        ('loans.create', 'Crear préstamos'),
        ('loans.edit', 'Editar préstamos'),
        ('loans.approve', 'Aprobar préstamos'),
        ('loans.reject', 'Rechazar préstamos'),
        ('loans.disburse', 'Desembolsar préstamos'),
        ('loans.calculator', 'Calculadora de préstamos'),
    ]),
    ('payments', 'Pagos', [
        ('payments.view', 'Ver pagos'),
        ('payments.create', 'Registrar pago'),
        ('payments.void', 'Anular pago'),
        ('payments.receipt', 'Ver recibos'),
    ]),
    ('collections', 'Cobranza', [
        ('collections.view', 'Ver cobranza'),
        ('collections.reminders', 'Crear recordatorios'),
        ('collections.contacts', 'Gestionar contactos'),
        ('collections.mobile', 'Cobrador móvil'),
        ('collections.supervise', 'Ver visitas de todos los cobradores'),
    ]),
    ('cashbox', 'Caja', [
        ('cashbox.view', 'Ver registros'),
        ('cashbox.open', 'Abrir sesión'),
        ('cashbox.close', 'Cerrar sesión'),
        ('cashbox.movements', 'Registrar movimientos'),
        ('cashbox.registers', 'Administrar cajas'),
    ]),
    ('contracts', 'Contratos', [
        ('contracts.view', 'Ver contratos'),
        ('contracts.create', 'Crear contratos'),
        ('contracts.templates', 'Editar plantillas'),
    ]),
    ('billing', 'Facturación', [
        ('billing.view', 'Ver facturas'),
        ('billing.create', 'Crear facturas'),
        ('billing.sign', 'Firmar e-CF'),
        ('billing.submit', 'Enviar a DGII'),
        ('billing.reports', 'Reportes 606/607'),
        ('billing.config', 'Configurar proveedor e-CF'),
    ]),
    ('comms', 'Comunicaciones', [
        ('comms.view', 'Ver mensajes'),
        ('comms.email', 'Enviar email'),
        ('comms.whatsapp', 'Enviar WhatsApp'),
        ('comms.tasks', 'Tareas (Kanban)'),
    ]),
    ('team', 'Equipo', [
        ('team.view', 'Ver miembros'),
        ('team.create', 'Crear miembros'),
        ('team.edit', 'Editar miembros'),
        ('team.delete', 'Eliminar miembros'),
        ('team.assign_roles', 'Asignar roles'),
    ]),
    ('settings', 'Configuración', [
        ('settings.view', 'Ver configuración'),
        ('settings.edit', 'Editar configuración'),
        ('settings.audit', 'Ver auditoría'),
    ]),
    ('ai', 'Asistente IA', [
        ('ai.access', 'Acceso al asistente'),
    ]),
]

CODE_LABELS = {code: label for _, _, items in MODULES for code, label in items}
ALL_CODES = frozenset(CODE_LABELS)

# Roles de sistema: clave → (nombre, descripción). La clave coincide con `User.role`.
SYSTEM_ROLES = {
    'admin': ('Administrador', 'Acceso completo a la financiera.'),
    'manager': ('Gerente', 'Gestiona préstamos, cobranza, caja y auditoría.'),
    'loan_officer': ('Oficial de crédito', 'Origina, aprueba y desembolsa préstamos.'),
    'collector': ('Cobrador', 'Cobra en ruta: pagos, visitas y contactos.'),
    'collection_supervisor': ('Supervisor de cobros', 'Supervisa a los cobradores y su cartera.'),
    'accountant': ('Contador', 'Facturación fiscal y caja.'),
    'cashier': ('Cajero', 'Opera la caja y registra pagos.'),
    'viewer': ('Solo lectura', 'Consulta sin modificar nada.'),
}

# Grupos de roles de los chequeos de hoy (sin admin, que recibe ALL_CODES).
_TODOS = {'manager', 'loan_officer', 'collector', 'collection_supervisor', 'accountant', 'cashier', 'viewer'}
_PRESTAMOS = {'manager', 'loan_officer'}                                     # CanManageLoans / CanApproveLoan
_COBRANZA = {'manager', 'loan_officer', 'collector', 'collection_supervisor'}  # CanManageCollections y afines
_PAGOS = _COBRANZA | {'cashier'}                                             # CanRegisterPayments
_CAJA = {'manager', 'accountant', 'cashier'}                                 # CanManageCashOperations
_FACTURACION = {'accountant'}                                                # CanManageBilling
_SUPERVISION = {'manager', 'collection_supervisor'}                          # COLLECTOR_OVERSIGHT_ROLES
_AUDITORIA = {'manager'}                                                     # audit/views.py
_SOLO_ADMIN = set()                                                          # dueño/admin

# Código → roles (además de admin) que lo tienen por defecto.
_ROLES_POR_CODIGO = {
    'customers.view': _TODOS,
    'customers.create': _PRESTAMOS,
    'customers.edit': _PRESTAMOS,
    'customers.delete': _PRESTAMOS,
    'customers.documents.view': _TODOS,
    'customers.documents.verify': _PRESTAMOS,
    'customers.statement': _TODOS,       # sin caso en la matriz: el GET es lectura abierta hoy
    'loans.view': _TODOS,
    'loans.create': _PRESTAMOS,
    'loans.edit': _PRESTAMOS,
    'loans.approve': _PRESTAMOS,
    'loans.reject': _PRESTAMOS,
    'loans.disburse': _PRESTAMOS,
    'loans.calculator': _TODOS,          # sin caso: LoanCalculatorView sólo pide autenticación
    'payments.view': _TODOS,
    'payments.create': _PAGOS,
    'payments.void': _PRESTAMOS,         # confirmar/cancelar pago (CanManageLoans hoy)
    'payments.receipt': _TODOS,          # sin caso: el recibo es un GET de lectura abierta
    'collections.view': _TODOS,
    'collections.reminders': _COBRANZA,
    'collections.contacts': _COBRANZA,
    'collections.mobile': _COBRANZA,
    'collections.supervise': _SUPERVISION,
    'cashbox.view': _TODOS,
    'cashbox.open': _CAJA,
    'cashbox.close': _CAJA,
    'cashbox.movements': _CAJA,
    'cashbox.registers': _SOLO_ADMIN,
    'contracts.view': _TODOS,
    'contracts.create': _PRESTAMOS,
    'contracts.templates': _PRESTAMOS,
    'billing.view': _TODOS,
    'billing.create': _FACTURACION,
    'billing.sign': _FACTURACION,
    'billing.submit': _FACTURACION,
    'billing.reports': _TODOS,           # sin caso: los 606/607 son GET de lectura abierta hoy
    'billing.config': _SOLO_ADMIN,
    'comms.view': _TODOS,
    'comms.email': _COBRANZA,            # sin caso: como CanSendMessages (WhatsApp)
    'comms.whatsapp': _COBRANZA,
    'comms.tasks': _COBRANZA,
    'team.view': _TODOS,
    'team.create': _SOLO_ADMIN,
    'team.edit': _SOLO_ADMIN,
    'team.delete': _SOLO_ADMIN,
    'team.assign_roles': _SOLO_ADMIN,
    'settings.view': _TODOS,
    'settings.edit': _SOLO_ADMIN,
    'settings.audit': _AUDITORIA,
    'ai.access': _TODOS,                 # sin caso: el chat de IA sólo pide autenticación
}
assert set(_ROLES_POR_CODIGO) == ALL_CODES, set(_ROLES_POR_CODIGO) ^ ALL_CODES

DEFAULT_ROLE_PERMISSIONS = {
    role: frozenset(code for code, roles in _ROLES_POR_CODIGO.items() if role in roles)
    for role in SYSTEM_ROLES
}
DEFAULT_ROLE_PERMISSIONS['admin'] = ALL_CODES
