"""Aprovisiona los registros de tenants pendientes (los recibidos por encima del tope diario)."""
import logging

from django.core.management.base import BaseCommand, CommandError

from apps.tenants.models import Tenant
from apps.tenants.provisioning import provision_pending_tenant

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Crea el schema y activa los tenants con registro pendiente (los más antiguos primero).'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None,
                            help='Máximo de tenants a aprovisionar en esta ejecución (1 o más).')

    def handle(self, *args, limit=None, **options):
        if limit is not None and limit < 1:
            raise CommandError('--limit debe ser 1 o más.')
        pending = Tenant.objects.filter(provisioning_pending=True).order_by('pending_since', 'pk')
        pks = pending.values_list('pk', flat=True)
        pks = list(pks[:limit] if limit is not None else pks)
        provisioned = failed = 0
        for pk in pks:
            try:
                if provision_pending_tenant(pk):
                    provisioned += 1
            except Exception:
                failed += 1
                logger.exception('No se pudo aprovisionar el tenant pendiente id=%s', pk)
                self.stderr.write(f'Error al aprovisionar el tenant id={pk}')
        logger.info('Tenants pendientes aprovisionados: %s, con error: %s', provisioned, failed)
        self.stdout.write(f'Tenants aprovisionados: {provisioned}. Con error: {failed}.')
