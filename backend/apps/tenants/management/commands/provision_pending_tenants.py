"""Aprovisiona los registros de tenants pendientes (los recibidos por encima del tope diario)."""
import logging

from django.core.management.base import BaseCommand

from apps.tenants.models import Tenant
from apps.tenants.provisioning import provision_pending_tenant

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Crea el schema y activa los tenants con registro pendiente (los más antiguos primero).'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None,
                            help='Máximo de tenants a aprovisionar en esta ejecución.')

    def handle(self, *args, limit=None, **options):
        pending = Tenant.objects.filter(provisioning_pending=True).order_by('pending_since', 'pk')
        pks = list(pending.values_list('pk', flat=True)[:limit] if limit else pending.values_list('pk', flat=True))
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
