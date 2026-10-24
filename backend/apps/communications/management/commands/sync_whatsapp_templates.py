"""
Crea/actualiza en Meta las plantillas de WhatsApp del catálogo para cada financiera.

    python manage.py sync_whatsapp_templates [--tenant <schema>]
"""
from django.core.management.base import BaseCommand

from apps.communications.tasks import sync_whatsapp_templates


class Command(BaseCommand):
    help = 'Sincroniza las plantillas de WhatsApp (Utility) con la cuenta de cada financiera'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=str, help='Schema del tenant (por defecto, todos)')

    def handle(self, *args, **options):
        result = sync_whatsapp_templates(options.get('tenant'))
        for schema, summary in result['results'].items():
            self.stdout.write(
                f"{schema}: creadas {len(summary['created'])}, actualizadas {len(summary['updated'])}, "
                f"errores {len(summary['errors'])}"
            )
            for name in summary['errors']:
                self.stdout.write(self.style.ERROR(f"  ✗ {name}"))
        for schema in result['failed']:
            self.stdout.write(self.style.ERROR(f"{schema}: falló la sincronización (ver logs)"))
        if not result['results'] and not result['failed']:
            self.stdout.write('Ningún tenant tiene credenciales completas de WhatsApp.')
