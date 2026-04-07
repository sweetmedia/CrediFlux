"""
Management command to update Django Site based on BACKEND_URL environment variable
This ensures email links use the correct domain instead of localhost
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings
from urllib.parse import urlparse


class Command(BaseCommand):
    help = 'Update Django Site domain based on BACKEND_URL environment variable'

    def handle(self, *args, **options):
        backend_url = settings.BACKEND_URL
        parsed_url = urlparse(backend_url)

        # Extract domain (with port if present)
        domain = parsed_url.netloc if parsed_url.netloc else 'localhost:8000'

        # Get or create the site
        try:
            site = Site.objects.get(pk=settings.SITE_ID)
            old_domain = site.domain
            site.domain = domain
            # Use shorter name to fit varchar(50) limit
            site.name = 'CrediFlux'
            site.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Site updated successfully:\n'
                    f'  Old domain: {old_domain}\n'
                    f'  New domain: {domain}\n'
                    f'  Protocol: {settings.ACCOUNT_DEFAULT_HTTP_PROTOCOL}'
                )
            )
        except Site.DoesNotExist:
            site = Site.objects.create(
                pk=settings.SITE_ID,
                domain=domain,
                name='CrediFlux'
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Site created successfully:\n'
                    f'  Domain: {domain}\n'
                    f'  Protocol: {settings.ACCOUNT_DEFAULT_HTTP_PROTOCOL}'
                )
            )

        self.stdout.write(
            self.style.WARNING(
                f'\n📧 Email confirmation links will now use:\n'
                f'  {settings.ACCOUNT_DEFAULT_HTTP_PROTOCOL}://{domain}/api/auth/registration/account-confirm-email/...'
            )
        )
