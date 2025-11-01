"""
Custom allauth adapters to use Site domain for email confirmation URLs
"""
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.contrib.sites.models import Site
from urllib.parse import urlparse, urlunparse


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter that forces email confirmation URLs
    to use the configured Site domain instead of request.get_host()
    """

    def get_email_confirmation_url(self, request, emailconfirmation):
        """
        Override to use Site domain instead of request.get_host()
        This ensures email links use the correct domain (e.g., Cloudflare tunnel URL)
        instead of localhost:8000 when running in Docker
        """
        # Get the default URL from parent (handles both EmailConfirmation and EmailConfirmationHMAC)
        url = super().get_email_confirmation_url(request, emailconfirmation)

        # Get the Site domain
        site = Site.objects.get_current()
        protocol = settings.ACCOUNT_DEFAULT_HTTP_PROTOCOL

        # Parse the URL and replace the netloc (domain) with our Site domain
        parsed = urlparse(url)
        replaced = parsed._replace(scheme=protocol, netloc=site.domain)

        return urlunparse(replaced)
