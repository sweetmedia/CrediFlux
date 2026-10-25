"""Borra los registros de tenants pendientes que nadie aprovisionó en N días.

Un pendiente reserva nombre, subdominio y correo del dueño. No tiene schema, así que basta
borrar la fila: el dominio y el usuario dueño caen en cascada. Aún no hay tarea Celery que lo
envuelva: correrlo a mano o desde cron (`manage.py expire_pending_registrations --days 7`).
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Borra los tenants con registro pendiente más antiguos que --days (7 por defecto).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7,
                            help='Antigüedad mínima, en días, del registro pendiente (1 o más).')

    def handle(self, *args, days=7, **options):
        if days < 1:
            raise CommandError('--days debe ser 1 o más.')
        cutoff = timezone.now() - timedelta(days=days)
        connection.set_schema_to_public()
        expired = 0
        with transaction.atomic():
            stale = Tenant.objects.select_for_update(of=('self',)).filter(
                provisioning_pending=True, pending_since__lt=cutoff,
            )
            for tenant in stale:
                # auto_drop_schema=False y sin schema: delete() sólo borra la fila (y la cascada).
                # La auditoría del borrado queda como fila de plataforma (tenant=None).
                tenant.delete()
                expired += 1
        logger.info('Registros de tenants pendientes expirados: %s (más de %s días)', expired, days)
        self.stdout.write(f'Registros pendientes expirados: {expired}.')
