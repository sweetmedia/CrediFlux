"""
User models extending Django's default User model
"""
from datetime import timedelta

from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from djmoney.models.fields import MoneyField
from decimal import Decimal
from apps.core.storage import tenant_upload_to


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
    avatar = models.ImageField(upload_to=tenant_upload_to('avatars'), max_length=255, blank=True, null=True)
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
        default_currency='DOP',
        null=True,
        blank=True,
        help_text='Meta diaria de cobros para el cobrador'
    )

    # Settings
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    receive_notifications = models.BooleanField(default=True)

    # Two-Factor Authentication
    totp_secret = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text='TOTP secret key for 2FA (Google Authenticator compatible)'
    )
    is_2fa_enabled = models.BooleanField(
        default=False,
        help_text='Whether two-factor authentication is enabled for this user'
    )
    backup_codes = models.JSONField(
        default=list,
        blank=True,
        help_text='List of backup codes for 2FA recovery'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    # Los JWT llevan este instante (claim `pwd_ts`); moverlo revoca los emitidos antes.
    password_changed_at = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def stamp_password_change(self):
        """Mueve `password_changed_at` a ahora (en memoria; lo guarda el llamador).

        Los JWT llevan `pwd_ts` en segundos: si el nuevo instante cae en el mismo
        segundo que el anterior, avanza un segundo para que el claim cambie.
        """
        now = timezone.now()
        previous = self.password_changed_at
        if previous is not None and int(now.timestamp()) <= int(previous.timestamp()):
            now = previous + timedelta(seconds=1)
        self.password_changed_at = now

    def set_password(self, raw_password):
        """Toda contraseña nueva (API, admin, shell...) invalida los JWT previos."""
        super().set_password(raw_password)
        self.stamp_password_change()

    def check_password(self, raw_password):
        """Como Django, pero el re-hash por cambio de hasher no revoca tokens."""
        def setter(raw):
            AbstractUser.set_password(self, raw)
            self._password = None
            self.save(update_fields=['password'])
        return check_password(raw_password, self.password, setter)

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
