"""Aprovisionamiento de registros de tenants que quedaron pendientes.

Por encima de MAX_TENANTS_PER_DAY el registro público no se rechaza: guarda el tenant sin
schema (`provisioning_pending=True`, inactivo, dueño inactivo). Lo usan la acción del admin
"Aprovisionar registros pendientes" y el comando `provision_pending_tenants`.
"""
import logging

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection, transaction
from django.utils import timezone
from django_tenants.utils import schema_exists

from .models import Tenant
from .serializers import _spend_daily_budget

logger = logging.getLogger(__name__)


def provision_pending_tenant(tenant_pk):
    """Crea el schema de un tenant pendiente y lo activa junto con su dueño.

    Decide sobre la fila bloqueada: si otro operador ya lo aprovisionó (o no está
    pendiente) devuelve False sin tocar nada. Un fallo al crear el schema o al migrar
    revierte la transacción (django-tenants borra el schema a medio crear) y se propaga.
    Un aprovisionamiento manual gasta el tope del día igual que uno automático.
    """
    with transaction.atomic():
        connection.set_schema_to_public()
        tenant = (
            Tenant.objects.select_for_update(of=('self',))
            .filter(pk=tenant_pk, provisioning_pending=True)
            .first()
        )
        if tenant is None:
            return False
        # Re-guardar un tenant existente con auto_create_schema y sin schema hace lo mismo
        # que el alta automática: CREATE SCHEMA + migrate_schemas + post_schema_sync.
        # Si el schema ya existe (creado a mano o por un intento previo), save() no lo
        # migraría: se migra explícitamente para no activar un tenant a medio construir.
        had_schema = schema_exists(tenant.schema_name)
        tenant.auto_create_schema = True
        tenant.provisioning_pending = False
        tenant.is_active = True
        tenant.save()
        if had_schema:
            call_command('migrate_schemas', tenant=True, schema_name=tenant.schema_name,
                         interactive=False, verbosity=0)
            connection.set_schema_to_public()
        get_user_model().objects.filter(tenant=tenant, is_tenant_owner=True).update(is_active=True)
    _spend_daily_budget(f'tenant_provisioning:{timezone.now():%Y%m%d}')
    logger.info('Tenant pendiente aprovisionado: %s (id=%s)', tenant.schema_name, tenant.pk)
    return True
