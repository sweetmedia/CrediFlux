"""
Registra en NexConnect el webhook de estado de facturas de un tenant.

    # URL armada desde la base pública de la API:
    python manage.py nexconnect_webhook_register --schema public \\
        --base-url https://api.crediflux.com

    # Reemplazar el webhook ya registrado (lo borra en NexConnect y crea otro):
    python manage.py nexconnect_webhook_register --schema public \\
        --base-url https://api.crediflux.com --replace

Usa la key de emisor del tenant (``nexconnect_configure``). El secret que
devuelve NexConnect se muestra una sola vez: se guarda cifrado en el tenant y
nunca se imprime. NexConnect exige URLs ``https://``.
"""
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse
from django_tenants.utils import get_tenant_model

from apps.billing.services.nexconnect.client import NexConnectClient, NexConnectError
from apps.billing.services.nexconnect.credentials import (
    NexConnectCredentialsError,
    credentials_for_tenant,
    set_tenant_webhook,
)
from apps.billing.services.nexconnect.webhooks import ALL_EVENTS, DEFAULT_SUBSCRIBED_EVENTS


def webhook_url(base_url: str, schema_name: str) -> str:
    path = reverse('nexconnect-webhook', kwargs={'schema_name': schema_name})
    return f'{base_url.rstrip("/")}{path}'


class Command(BaseCommand):
    help = 'Registra el webhook de NexConnect de un tenant (POST /v1/webhooks/) y guarda su secret cifrado'

    def add_arguments(self, parser):
        parser.add_argument('--schema', required=True, help='schema_name del tenant')
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument('--base-url', help='Base pública de la API de CrediFlux (https://…)')
        target.add_argument('--url', help='URL completa del endpoint (si no sigue la ruta estándar)')
        parser.add_argument('--events', default=','.join(DEFAULT_SUBSCRIBED_EVENTS),
                            help='Eventos separados por coma (por defecto, los de facturas emitidas)')
        parser.add_argument('--replace', action='store_true',
                            help='Borra en NexConnect el webhook ya registrado antes de crear el nuevo')

    def handle(self, *args, schema, base_url, url, events, replace, **options):
        Tenant = get_tenant_model()
        try:
            tenant = Tenant.objects.get(schema_name=schema)
        except Tenant.DoesNotExist:
            raise CommandError(f'No existe el tenant con schema "{schema}"')

        url = url or webhook_url(base_url, tenant.schema_name)
        if not url.startswith('https://'):
            raise CommandError('NexConnect solo acepta URLs https://')
        event_list = [e.strip() for e in events.split(',') if e.strip()]
        unknown = sorted(set(event_list) - set(ALL_EVENTS))
        if not event_list or unknown:
            raise CommandError(f'Eventos inválidos: {unknown or "(ninguno)"}')

        try:
            client = NexConnectClient(credentials_for_tenant(tenant))
        except NexConnectCredentialsError as e:
            raise CommandError(f'{e} (use nexconnect_configure primero)')

        previous_id = tenant.nexconnect_webhook_id
        if previous_id and not replace:
            raise CommandError(
                f'El tenant ya tiene el webhook {previous_id}; use --replace para sustituirlo'
            )
        if previous_id:
            try:
                client.delete_webhook(previous_id)
                self.stdout.write(f'Webhook anterior {previous_id} borrado en NexConnect')
            except NexConnectError as e:
                if e.status_code != 404:
                    raise CommandError(f'No se pudo borrar el webhook anterior: {e}')

        try:
            data = client.create_webhook(url, event_list, description=f'CrediFlux {tenant.schema_name}')
        except NexConnectError as e:
            raise CommandError(str(e))
        if not data.get('secret') or not data.get('id'):
            raise CommandError('NexConnect no devolvió id/secret del webhook')

        try:
            set_tenant_webhook(tenant, data['id'], data['secret'])
        except NexConnectCredentialsError as e:
            raise CommandError(str(e))
        self.stdout.write(self.style.SUCCESS(
            f'Webhook {data["id"]} registrado para "{schema}" → {url} '
            f'({len(event_list)} eventos; secret guardado cifrado)'
        ))
