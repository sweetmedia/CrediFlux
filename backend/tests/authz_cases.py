"""Matriz de autorización ACTUAL de la API de tenant (caracterización, D6).

Fija lo que cada rol puede hacer HOY, antes de cambiar los chequeos de rol por
permisos editables. Los pasos siguientes (resolutor de permisos y refactor de
cada app) deben dejar esta matriz pasando SIN CAMBIOS; `DEFAULT_ROLE_PERMISSIONS`
(Task 7) se deriva de `EXPECTED`.

* `CASES`: (nombre, método, ruta, cuerpo). La ruta puede llevar marcadores
  `{nombre}` que el test rellena con objetos creados para el caso (ver
  `OBJETOS` en `test_authz_matrix.py`). Para escrituras se manda un cuerpo
  inválido: si el permiso deja pasar, la respuesta es 400 (o 404 si el objeto
  no existe) y no se escribe nada.
* `EXPECTED`: caso → persona → códigos aceptados. Personas: los 8 roles más
  `owner` (dueño del tenant con rol `admin`, como lo crea el registro). Lo que
  importa es 403 frente a no-403; los conjuntos son tan estrechos como permite
  el comportamiento estable de hoy.
* `VISIBLE`: casos de alcance (no 403): caso → persona → si la respuesta
  incluye el objeto de otro usuario (`objeto` en `SCOPE_OBJECT`).
* `EXTRA_SETUP`: objetos que el caso necesita aunque no aparezcan en la ruta.

Fuera de alcance: los chequeos del admin de Django (`apps/loans/admin.py`,
`apps/users/admin.py`); esta matriz sólo cubre la API.
"""

ROLES = (
    'admin', 'manager', 'loan_officer', 'collector', 'collection_supervisor',
    'accountant', 'cashier', 'viewer',
)
PERSONAS = ROLES + ('owner',)

# Uuid que no existe: para acciones de detalle donde basta ver si el permiso deja pasar.
UUID_INEXISTENTE = '00000000-0000-0000-0000-000000000000'

CASES = [
    # --- Préstamos: aprobar / rechazar (CanApproveLoan, loans/permissions.py:8; views.py:476,562)
    ('prestamo_aprobar', 'POST', '/api/loans/{prestamo_activo}/approve/', {}),
    ('prestamo_rechazar', 'POST', '/api/loans/{prestamo_activo}/reject/', {}),
    # Desembolsar (CanApproveLoan, views.py:516) + maker-checker de policy.py:241-245: el
    # préstamo lo aprobó quien desembolsa; admin/dueño están exentos (200), el resto 400.
    ('prestamo_desembolsar_aprobado_por_mi', 'POST', '/api/loans/{prestamo_aprobado_por_mi}/disburse/', {}),

    # --- CanManageLoans (loans/permissions.py:62): escrituras; lectura abierta
    ('cliente_crear', 'POST', '/api/loans/customers/', {}),  # views.py:54
    ('cliente_documento_crear', 'POST', '/api/loans/customer-documents/', {}),  # views.py:175
    ('prestamo_crear', 'POST', '/api/loans/', {}),  # views.py:373
    ('garantia_crear', 'POST', '/api/loans/collaterals/', {}),  # views.py:1237
    ('plantilla_contrato_crear', 'POST', '/api/loans/contract-templates/', {}),  # views.py:1497
    ('contrato_crear', 'POST', '/api/loans/contracts/', {}),  # views.py:1564
    ('garante_crear', 'POST', '/api/loans/guarantors/', {}),  # views.py:2450
    ('pago_confirmar', 'POST', '/api/loans/payments/{pago_completado}/confirm/', {}),  # views.py:944
    ('pago_cancelar', 'POST', '/api/loans/payments/{pago_completado}/cancel/', {}),  # views.py:1040
    ('cliente_leer', 'GET', '/api/loans/customers/', {}),  # lectura abierta de CanManageLoans

    # --- CanRegisterPayments (loans/permissions.py:88; views.py:896)
    ('pago_registrar', 'POST', '/api/loans/payments/', {}),
    # Reverso: dueño o superusuario (views.py:1069), detrás de CanRegisterPayments del viewset.
    ('pago_revertir', 'POST', '/api/loans/payments/{pago_completado}/reverse/', {}),

    # --- CanManageCollections (loans/permissions.py:117): escrituras; lectura abierta
    ('recordatorio_crear', 'POST', '/api/loans/collection-reminders/', {}),  # views.py:1289
    ('contacto_cobro_crear', 'POST', '/api/loans/collection-contacts/', {}),  # views.py:1379
    ('telefono_cliente_crear', 'POST', '/api/loans/customer-phones/', {}),  # views.py:2479
    ('correo_cliente_crear', 'POST', '/api/loans/customer-emails/', {}),  # views.py:2487
    ('visita_cobrador_crear', 'POST', '/api/loans/collector-visits/', {}),  # views_geolocation.py:103
    ('ubicacion_cobrador_ping', 'POST', '/api/loans/collector-locations/ping/', {}),  # views_geolocation.py:190
    # Alcance de visitas: COLLECTOR_OVERSIGHT_ROLES (views_geolocation.py:23,28) ve las de otros.
    ('visitas_de_otro_cobrador', 'GET', '/api/loans/collector-visits/', {}),

    # --- CanLookupCedula (core/views.py:49): roles de cobranza, también en GET
    ('cedula_consultar', 'GET', '/api/validate-cedula/?cedula=1', {}),

    # --- CanManageCashOperations (cashbox/views.py:28): escrituras; lectura abierta
    ('caja_crear', 'POST', '/api/cashbox/registers/', {}),  # views.py:58
    # Borrar caja: además dueño/admin/superusuario (cashbox/views.py:65); la caja tiene turnos → 400.
    ('caja_borrar', 'DELETE', '/api/cashbox/registers/{caja_con_turnos}/', {}),
    ('turno_abrir', 'POST', '/api/cashbox/sessions/open/', {}),  # views.py:84
    ('turno_cerrar', 'POST', '/api/cashbox/sessions/{turno_cerrado}/close/', {}),  # views.py:121
    ('movimiento_caja_crear', 'POST', '/api/cashbox/movements/', {}),  # views.py:217
    ('conteo_denominaciones_crear', 'POST', '/api/cashbox/denominations/', {}),  # views.py:250

    # --- Ajustes del tenant: dueño/admin/superusuario (tenants/views.py:483)
    ('ajustes_tenant_editar', 'PATCH', '/api/tenants/settings/', {}),

    # --- Auditoría: rol admin/manager (audit/views.py:17 lista, :82 stats)
    ('auditoria_lista', 'GET', '/api/audit/', {}),
    ('auditoria_stats', 'GET', '/api/audit/stats/', {}),

    # --- Configuración IA: dueño/admin/superusuario (ai/views.py:283)
    ('ia_config_editar', 'PUT', '/api/ai/config/', {}),

    # --- CanManageBilling (billing/permissions.py:8): escrituras y acciones DGII aunque sean GET
    ('secuencia_fiscal_crear', 'POST', '/api/billing/sequences/', {}),  # billing/views.py:81
    ('factura_estado_dgii', 'GET', f'/api/billing/invoices/{UUID_INEXISTENTE}/dgii-status/', {}),  # :93
    ('secuencia_fiscal_leer', 'GET', '/api/billing/sequences/', {}),  # lectura abierta
    # Config del proveedor e-CF: CanManageBilling y además dueño/admin/superusuario (billing/views.py:425)
    ('proveedor_ecf_config_editar', 'PATCH', '/api/billing/ecf-provider/config/', {}),

    # --- Comunicaciones (communications/permissions.py)
    ('whatsapp_enviar', 'POST', '/api/communications/whatsapp/conversations/18095550000/send/', {}),  # CanSendMessages, views_whatsapp.py:167
    ('tarea_crear', 'POST', '/api/communications/tasks/', {}),  # CanManageTasks, communications/views.py:36
    ('tarea_leer', 'GET', '/api/communications/tasks/', {}),  # lectura abierta de CanManageTasks

    # --- Gestión de usuarios: can_manage_users() = dueño/admin/superusuario (users/models.py:173)
    ('usuario_crear', 'POST', '/api/users/team/create/', {}),  # users/views.py:512
    ('usuario_editar', 'PATCH', '/api/users/team/{usuario_destino}/', {}),  # users/views.py:650
    ('usuario_desactivar', 'DELETE', '/api/users/team/{usuario_destino}/', {}),  # users/views.py:682
    # Asignar rol admin: sólo dueño/superusuario (users/serializers.py:688; también :618 en el alta)
    ('usuario_asignar_admin', 'PATCH', '/api/users/team/{usuario_destino}/', {'role': 'admin'}),
    # El rol del dueño no cambia (users/serializers.py:682)
    ('dueno_cambiar_rol', 'PATCH', '/api/users/team/{dueno_destino}/', {'role': 'manager'}),
    # El dueño no se desactiva (users/serializers.py:700)
    ('dueno_desactivar', 'PATCH', '/api/users/team/{dueno_destino}/', {'is_active': False}),
]

CASE_NAMES = [case[0] for case in CASES]


def _matrix(allowed, ok, denied=frozenset({403})):
    """Persona → códigos: `ok` para las personas de `allowed`, `denied` para el resto."""
    return {p: set(ok) if p in allowed else set(denied) for p in PERSONAS}


# Grupos de personas que pasan cada chequeo de hoy (el dueño pasa siempre: bypass o rol admin).
APPROVERS = {'admin', 'manager', 'loan_officer', 'owner'}                    # CanApproveLoan
LOAN_MANAGERS = {'admin', 'manager', 'loan_officer', 'owner'}                # CanManageLoans
PAYMENT_TAKERS = {'admin', 'manager', 'loan_officer', 'collector',
                  'collection_supervisor', 'cashier', 'owner'}               # CanRegisterPayments
COLLECTIONS = {'admin', 'manager', 'loan_officer', 'collector',
               'collection_supervisor', 'owner'}                             # CanManageCollections y afines
CASH = {'admin', 'manager', 'accountant', 'cashier', 'owner'}               # CanManageCashOperations
OWNER_ADMIN = {'admin', 'owner'}                                             # dueño/admin(/superusuario)
OWNER_ONLY = {'owner'}                                                       # dueño(/superusuario)
BILLING = {'admin', 'accountant', 'owner'}                                   # CanManageBilling
AUDIT = {'admin', 'manager', 'owner'}                                        # rol admin/manager
OVERSIGHT = {'admin', 'manager', 'collection_supervisor', 'owner'}           # COLLECTOR_OVERSIGHT_ROLES
EVERYONE = set(PERSONAS)

EXPECTED = {
    'prestamo_aprobar': _matrix(APPROVERS, {400}),
    'prestamo_rechazar': _matrix(APPROVERS, {400}),
    # Pasa CanApproveLoan; admin/dueño exentos del maker-checker → 200; manager/oficial → 400.
    'prestamo_desembolsar_aprobado_por_mi': {
        **_matrix(APPROVERS, {400}),
        'admin': {200},
        'owner': {200},
    },

    'cliente_crear': _matrix(LOAN_MANAGERS, {400}),
    'cliente_documento_crear': _matrix(LOAN_MANAGERS, {400}),
    'prestamo_crear': _matrix(LOAN_MANAGERS, {400}),
    'garantia_crear': _matrix(LOAN_MANAGERS, {400}),
    'plantilla_contrato_crear': _matrix(LOAN_MANAGERS, {400}),
    'contrato_crear': _matrix(LOAN_MANAGERS, {400}),
    'garante_crear': _matrix(LOAN_MANAGERS, {400}),
    'pago_confirmar': _matrix(LOAN_MANAGERS, {400}),
    'pago_cancelar': _matrix(LOAN_MANAGERS, {400}),
    'cliente_leer': _matrix(EVERYONE, {200}),

    'pago_registrar': _matrix(PAYMENT_TAKERS, {400}),
    # Sin `reason` el dueño recibe 400; el admin que no es dueño, 403.
    'pago_revertir': _matrix(OWNER_ONLY, {400}),

    'recordatorio_crear': _matrix(COLLECTIONS, {400}),
    'contacto_cobro_crear': _matrix(COLLECTIONS, {400}),
    'telefono_cliente_crear': _matrix(COLLECTIONS, {400}),
    'correo_cliente_crear': _matrix(COLLECTIONS, {400}),
    'visita_cobrador_crear': _matrix(COLLECTIONS, {400}),
    'ubicacion_cobrador_ping': _matrix(COLLECTIONS, {400}),
    'visitas_de_otro_cobrador': _matrix(EVERYONE, {200}),  # alcance en VISIBLE

    'cedula_consultar': _matrix(COLLECTIONS, {400}),

    'caja_crear': _matrix(CASH, {400}),
    # Gerente/contabilidad/caja pasan la clase pero el borrado exige dueño/admin → 403.
    'caja_borrar': _matrix(OWNER_ADMIN, {400}),
    'turno_abrir': _matrix(CASH, {400}),
    'turno_cerrar': _matrix(CASH, {400}),
    'movimiento_caja_crear': _matrix(CASH, {400}),
    'conteo_denominaciones_crear': _matrix(CASH, {400}),

    'ajustes_tenant_editar': _matrix(OWNER_ADMIN, {200}),

    'auditoria_lista': _matrix(EVERYONE, {200}),  # alcance en VISIBLE
    'auditoria_stats': _matrix(AUDIT, {200}),

    'ia_config_editar': _matrix(OWNER_ADMIN, {200}),

    'secuencia_fiscal_crear': _matrix(BILLING, {400}),
    'factura_estado_dgii': _matrix(BILLING, {404}),
    'secuencia_fiscal_leer': _matrix(EVERYONE, {200}),
    # Contabilidad pasa CanManageBilling pero la vista exige dueño/admin → 403.
    'proveedor_ecf_config_editar': _matrix(OWNER_ADMIN, {200}),

    'whatsapp_enviar': _matrix(COLLECTIONS, {400}),
    'tarea_crear': _matrix(COLLECTIONS, {400}),
    'tarea_leer': _matrix(EVERYONE, {200}),

    'usuario_crear': _matrix(OWNER_ADMIN, {400}),
    'usuario_editar': _matrix(OWNER_ADMIN, {200}),
    'usuario_desactivar': _matrix(OWNER_ADMIN, {200}),
    # El admin que no es dueño llega al serializer y recibe 400; el dueño lo asigna.
    'usuario_asignar_admin': {**_matrix(OWNER_ADMIN, {400}), 'owner': {200}},
    'dueno_cambiar_rol': _matrix(OWNER_ADMIN, {400}),
    'dueno_desactivar': _matrix(OWNER_ADMIN, {400}),
}

# Casos de alcance: ¿la respuesta incluye el objeto de otro usuario?
SCOPE_OBJECT = {
    'visitas_de_otro_cobrador': 'visita_ajena',      # views_geolocation.py:23,28
    'auditoria_lista': 'registro_auditoria',         # audit/views.py:17
}
VISIBLE = {
    'visitas_de_otro_cobrador': {p: p in OVERSIGHT for p in PERSONAS},
    'auditoria_lista': {p: p in AUDIT for p in PERSONAS},
}

# Objetos que el caso necesita además de los marcadores de su ruta.
EXTRA_SETUP = {
    'visitas_de_otro_cobrador': ['visita_ajena'],
    'auditoria_lista': ['registro_auditoria'],
    'prestamo_desembolsar_aprobado_por_mi': ['politica_permisiva'],
}

assert set(EXPECTED) == set(CASE_NAMES), set(EXPECTED) ^ set(CASE_NAMES)
assert len(CASE_NAMES) == len(set(CASE_NAMES))
assert all(set(row) == set(PERSONAS) for row in EXPECTED.values())
