"""Crea (o completa) el tenant del schema `public` y su dominio primario.

Paso de arranque de una base nueva, después de `migrate_schemas --shared`: django-tenants necesita
una fila `Tenant` para `public` y un `Domain` con el host público (p. ej. `app.crediflux.com.do`)
para resolver ese host a `urls_public`. Idempotente: si ya existen, sólo asegura que el dominio
indicado apunte a `public` y sea el primario.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.tenants.models import Domain, Tenant


class Command(BaseCommand):
    help = 'Crea el tenant público (schema public) y su dominio primario. Idempotente.'

    def add_arguments(self, parser):
        parser.add_argument('--domain', required=True, help='Host público, p. ej. app.crediflux.com.do')
        parser.add_argument('--email', default='admin@crediflux.com.do', help='Correo de contacto del tenant público.')

    def handle(self, *args, domain, email, **options):
        domain = domain.strip().lower()
        if not domain or '/' in domain or ':' in domain:
            raise CommandError('--domain es sólo el host, sin esquema ni puerto.')
        connection.set_schema_to_public()
        with transaction.atomic():
            tenant, created = Tenant.objects.get_or_create(
                schema_name='public',
                defaults={'name': 'CrediFlux (public)', 'business_name': 'CrediFlux', 'email': email},
            )
            other = Domain.objects.filter(domain=domain).exclude(tenant=tenant).first()
            if other is not None:
                raise CommandError(f'{domain} ya pertenece al tenant {other.tenant.schema_name}.')
            Domain.objects.filter(tenant=tenant, is_primary=True).exclude(domain=domain).update(is_primary=False)
            Domain.objects.update_or_create(domain=domain, defaults={'tenant': tenant, 'is_primary': True})
        self.stdout.write(self.style.SUCCESS(
            f'Tenant public {"creado" if created else "ya existía"}; dominio primario {domain}.'
        ))
