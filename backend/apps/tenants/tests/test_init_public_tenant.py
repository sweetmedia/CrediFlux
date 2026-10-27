"""`init_public_tenant`: arranque del tenant público en una base nueva (idempotente)."""
import pytest
from django.core.management import CommandError, call_command

from apps.tenants.models import Domain, Tenant


@pytest.mark.django_db
def test_sets_the_given_domain_as_primary_for_public_and_is_idempotent(public_schema):
    call_command('init_public_tenant', '--domain', 'App.Crediflux.test')
    call_command('init_public_tenant', '--domain', 'app.crediflux.test')

    public = Tenant.objects.get(schema_name='public')
    assert Tenant.objects.filter(schema_name='public').count() == 1
    primary = Domain.objects.get(tenant=public, is_primary=True)
    assert primary.domain == 'app.crediflux.test'
    assert Domain.objects.filter(domain='app.crediflux.test').count() == 1


@pytest.mark.django_db
def test_refuses_a_domain_owned_by_another_tenant(public_schema, tenant):
    taken = tenant.domains.first().domain
    with pytest.raises(CommandError):
        call_command('init_public_tenant', '--domain', taken)
    assert Domain.objects.get(domain=taken).tenant_id == tenant.pk


@pytest.mark.django_db
def test_refuses_a_url_instead_of_a_host(public_schema):
    with pytest.raises(CommandError):
        call_command('init_public_tenant', '--domain', 'https://app.crediflux.test')
