"""
User models extending Django's default User model
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from djmoney.models.fields import MoneyField
from decimal import Decimal


class User(AbstractUser):
    """
    Extended User model with additional fields for the SaaS platform.

    Users can be:
    - Superusers: System administrators (no tenant)
    - Tenant Owners: Company administrators who created/own a tenant
    - Staff Users: Employees created by tenant owners
    """
    email = models.EmailField(unique=True)
    phone = PhoneNumberField(blank=True, null=True)

    # Tenant relationship
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
        help_text='Tenant this user belongs to. Null for superusers.'
    )
    is_tenant_owner = models.BooleanField(
        default=False,
        help_text='True if this user is the owner/creator of the tenant'
    )

    # Profile information
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

    # Role and permissions (within their tenant)
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('loan_officer', 'Loan Officer'),
        ('collector', 'Cobrador'),                              # NEW
        ('collection_supervisor', 'Supervisor de Cobranza'),    # NEW
        ('accountant', 'Accountant'),
        ('cashier', 'Cashier'),
        ('viewer', 'Viewer'),
    ]
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='viewer')

    # Collection-specific fields (for collectors and collection supervisors)
    collection_zone = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Zona de cobranza asignada (ej: Zona Norte, Zona Este, etc.)'
    )

    daily_collection_target = MoneyField(
        max_digits=12,
        decimal_places=2,
        default_currency='USD',
        null=True,
        blank=True,
        help_text='Meta diaria de cobros para el cobrador'
    )

    # Settings
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    receive_notifications = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def is_admin(self):
        """Check if user is an admin (tenant admin or system superuser)"""
        return self.role == 'admin' or self.is_tenant_owner or self.is_superuser

    @property
    def is_manager(self):
        """Check if user is a manager or above"""
        return self.role in ['admin', 'manager'] or self.is_tenant_owner or self.is_superuser

    @property
    def is_system_admin(self):
        """Check if user is a system administrator (superuser with no tenant)"""
        return self.is_superuser and self.tenant is None

    @property
    def tenant_name(self):
        """Get the name of the user's tenant"""
        return self.tenant.name if self.tenant else 'System'

    def can_manage_users(self):
        """Check if user can create/edit users in their tenant"""
        return self.is_tenant_owner or self.role == 'admin' or self.is_superuser

    def belongs_to_tenant(self, tenant):
        """Check if user belongs to a specific tenant"""
        return self.tenant == tenant if tenant else False
