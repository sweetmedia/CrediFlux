"""
Crea (o actualiza) las plantillas de contrato de sistema en uno o todos los tenants.

    python manage.py seed_contract_templates --schema caproinsa
    python manage.py seed_contract_templates --all
    python manage.py seed_contract_templates --all --overwrite   # pisa el contenido editado

Es idempotente: identifica cada plantilla por su nombre y, sin --overwrite,
no toca las que el tenant ya tiene (pudo haberlas editado).
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / 'contract_templates'

SYSTEM_TEMPLATES = [
    {
        'name': 'Pagaré notarial con co-deudor',
        'file': 'pagare_notarial_codeudor.txt',
        'description': (
            'Pagaré notarial con deudor y co-deudor solidarios por el monto total con interés. '
            'Usa el primer garante del préstamo como co-deudor. Completa los datos del notario '
            'y el estado civil antes de imprimir.'
        ),
        'includes_signatures': True,
    },
]


class Command(BaseCommand):
    help = 'Crea las plantillas de contrato de sistema en uno o todos los tenants'

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument('--schema', help='Schema del tenant')
        target.add_argument('--all', action='store_true', help='Todos los tenants (excepto public)')
        parser.add_argument('--overwrite', action='store_true',
                            help='Reemplaza el contenido de las plantillas que ya existen')

    def handle(self, *args, **options):
        Tenant = get_tenant_model()
        if options['all']:
            schemas = list(
                Tenant.objects.exclude(schema_name=get_public_schema_name())
                .values_list('schema_name', flat=True)
            )
        else:
            if not Tenant.objects.filter(schema_name=options['schema']).exists():
                raise CommandError(f"No existe el tenant con schema '{options['schema']}'")
            schemas = [options['schema']]

        for schema in schemas:
            with schema_context(schema):
                self._seed(schema, options['overwrite'])

    def _seed(self, schema, overwrite):
        from apps.loans.models_contracts import ContractTemplate

        for spec in SYSTEM_TEMPLATES:
            content = (TEMPLATES_DIR / spec['file']).read_text(encoding='utf-8')
            template = ContractTemplate.objects.filter(name=spec['name']).first()
            if template and not overwrite:
                self.stdout.write(f"[{schema}] '{spec['name']}' ya existe, sin cambios")
                continue

            if template is None:
                template = ContractTemplate(name=spec['name'])
            template.description = spec['description']
            template.content = content
            template.includes_signatures = spec['includes_signatures']
            template.save()
            self.stdout.write(self.style.SUCCESS(f"[{schema}] '{spec['name']}' guardada"))
