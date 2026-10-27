"""Custom allauth adapter for multi-tenant email confirmation URLs."""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context as allauth_context
from django.conf import settings
from django.contrib.sites.models import Site
from django.db import connection
from urllib.parse import urlparse, urlunparse


class TenantSite:
    def __init__(self, domain, name):
        self.domain = domain
        self.name = name


class CustomAccountAdapter(DefaultAccountAdapter):
    """Build allauth email links/content using the current tenant domain."""

    def _get_request(self, request=None):
        return request or getattr(allauth_context, 'request', None)

    def _is_local_host(self, host):
        return not host or 'localhost' in host or host.startswith('127.0.0.1')

    def _get_tenant_domain(self, request=None):
        """Priority: request host > tenant primary domain > Site domain > fallback."""
        request = self._get_request(request)

        if request:
            try:
                host = request.get_host()
                if host:
                    return host
            except Exception:
                pass

        try:
            tenant = getattr(connection, 'tenant', None)
            if tenant:
                from apps.tenants.models import Domain
                domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
                if domain and domain.domain:
                    return domain.domain
        except Exception:
            pass

        try:
            return Site.objects.get_current().domain
        except Exception:
            return 'app.crediflux.com.do'

    def _get_tenant_name(self):
        try:
            tenant = getattr(connection, 'tenant', None)
            if tenant:
                return tenant.business_name or tenant.name
        except Exception:
            pass
        try:
            return Site.objects.get_current().name
        except Exception:
            return 'CrediFlux'

    def _get_protocol(self, request=None, domain=None):
        request = self._get_request(request)
        if request:
            try:
                if request.is_secure():
                    return 'https'
            except Exception:
                pass
        domain = domain or self._get_tenant_domain(request)
        if self._is_local_host(domain):
            return 'http'
        return 'https'

    def _get_current_site(self, request=None):
        domain = self._get_tenant_domain(request)
        return TenantSite(domain=domain, name=self._get_tenant_name())

    def get_from_email(self):
        tenant = getattr(connection, 'tenant', None)
        if tenant and getattr(tenant, 'notification_email_from', None):
            return tenant.notification_email_from
        return getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@crediflux.com.do')

    def format_email_subject(self, subject):
        prefix = f'[{self._get_current_site().name}] '
        return prefix + subject

    def get_email_confirmation_url(self, request, emailconfirmation):
        """Enlace de confirmación en el host del tenant del USUARIO, no en el de quien lo envía.

        `CustomConfirmEmailView` sólo confirma en el host del tenant del usuario (ronda 30), y el
        admin que reenvía la verificación suele estar en el host público. La ruta
        (`account-confirm-email/<key>/`) la sirve el backend: host = dominio del tenant
        (`tenant_backend_url`), scheme y puerto de `BACKEND_URL`. Un usuario sin tenant sigue con el
        host de la petición (el admin de plataforma, en el público).
        """
        url = super().get_email_confirmation_url(request, emailconfirmation)
        user = emailconfirmation.email_address.user
        if user.tenant_id:
            from apps.tenants.links import tenant_backend_url
            base = urlparse(tenant_backend_url(user.tenant))
            return urlunparse(urlparse(url)._replace(scheme=base.scheme, netloc=base.netloc))
        domain = self._get_tenant_domain(request)
        protocol = self._get_protocol(request, domain)
        parsed = urlparse(url)
        return urlunparse(parsed._replace(scheme=protocol, netloc=domain))

    def send_mail(self, template_prefix, email, context, **kwargs):
        context = dict(context)
        context['current_site'] = self._get_current_site()
        return super().send_mail(template_prefix, email, context, **kwargs)

