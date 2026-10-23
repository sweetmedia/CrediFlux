"""
Configura NexConnect como proveedor e-CF de un tenant.

    # Toma la key de la variable de entorno NEXCONNECT_API_KEY (no queda en el historial):
    python manage.py nexconnect_configure --schema public --from-env

    # Solo probar la conexión con la key ya guardada:
    python manage.py nexconnect_configure --schema public --check
"""
import os

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_tenant_model, schema_context

from apps.billing.services.nexconnect.credentials import (
    NexConnectCredentialsError,
    set_tenant_api_key,
)
from apps.billing.services.nexconnect.provider import PROVIDER_KEY, NexConnectProvider


class Command(BaseCommand):
    help = 'Guarda (cifrada) la API key de emisor de NexConnect de un tenant y prueba la conexión'

    def add_arguments(self, parser):
        parser.add_argument('--schema', required=True, help='schema_name del tenant')
        parser.add_argument('--from-env', action='store_true',
                            help='Lee la key de la variable de entorno NEXCONNECT_API_KEY')
        parser.add_argument('--check', action='store_true',
                            help='No cambia nada; solo prueba la conexión')

    def handle(self, *args, schema, from_env, check, **options):
        Tenant = get_tenant_model()
        try:
            tenant = Tenant.objects.get(schema_name=schema)
        except Tenant.DoesNotExist:
            raise CommandError(f'No existe el tenant con schema "{schema}"')

        if not check:
            if not from_env:
                raise CommandError('Indique --from-env (la key nunca se pasa por argumento)')
            api_key = os.environ.get('NEXCONNECT_API_KEY', '')
            if not api_key:
                raise CommandError('NEXCONNECT_API_KEY no está definida')
            try:
                set_tenant_api_key(tenant, api_key, save=False)
            except NexConnectCredentialsError as e:
                raise CommandError(str(e))
            tenant.ecf_provider = PROVIDER_KEY
            tenant.save(update_fields=['ecf_provider', 'ecf_provider_api_key'])
            self.stdout.write(self.style.SUCCESS(
                f'NexConnect configurado para "{schema}" (key cifrada guardada)'
            ))

        with schema_context(tenant.schema_name):
            result = NexConnectProvider(tenant).test_connection()
        style = self.style.SUCCESS if result.get('status') == 'online' else self.style.ERROR
        self.stdout.write(style(
            ', '.join(f'{k}={v}' for k, v in result.items())
        ))
        if result.get('status') != 'online':
            raise CommandError('No se pudo conectar con NexConnect')
