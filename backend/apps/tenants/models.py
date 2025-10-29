"""
Tenant models for multi-tenant architecture
"""
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Tenant(TenantMixin):
    """
    Tenant model representing a company/organization using the platform.
    Each tenant has its own isolated database schema.
    """
    name = models.CharField(max_length=100, unique=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    # Business information
    business_name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Address
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    # Settings
    is_active = models.BooleanField(default=True)
    max_users = models.IntegerField(default=10)
    subscription_plan = models.CharField(
        max_length=50,
        choices=[
            ('basic', 'Basic'),
            ('professional', 'Professional'),
            ('enterprise', 'Enterprise'),
        ],
        default='basic'
    )

    # Logo and branding
    logo = models.ImageField(upload_to='tenants/logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#6366f1')

    # Automatically create schema on save
    auto_create_schema = True
    auto_drop_schema = False

    class Meta:
        db_table = 'tenants'
        ordering = ['-created_on']

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    """
    Domain model linking domains/subdomains to tenants.
    Example: company1.crediflux.com -> Company1 tenant
    """
    pass

    class Meta:
        db_table = 'tenant_domains'

    def __str__(self):
        return self.domain
