import uuid
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    Model to track all important actions in the system.
    Used for compliance, security, and accountability.
    """

    ACTION_CHOICES = [
        # CRUD Operations
        ('create', 'Crear'),
        ('update', 'Actualizar'),
        ('delete', 'Eliminar'),
        # Loan Operations
        ('approve', 'Aprobar'),
        ('reject', 'Rechazar'),
        ('disburse', 'Desembolsar'),
        ('close', 'Cerrar'),
        # Payment Operations
        ('payment', 'Pago'),
        ('payment_void', 'Anular Pago'),
        # Authentication
        ('login', 'Iniciar Sesion'),
        ('logout', 'Cerrar Sesion'),
        ('login_failed', 'Login Fallido'),
        # Security
        ('password_change', 'Cambio de Contrasena'),
        ('password_reset', 'Reseteo de Contrasena'),
        ('2fa_enable', 'Habilitar 2FA'),
        ('2fa_disable', 'Deshabilitar 2FA'),
        # Permission Changes
        ('permission_change', 'Cambio de Permisos'),
        ('role_change', 'Cambio de Rol'),
        # Other
        ('export', 'Exportar'),
        ('import', 'Importar'),
        ('config_change', 'Cambio de Configuracion'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='audit_logs',
        help_text='Tenant to which this log belongs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text='User who performed the action'
    )
    user_email = models.EmailField(
        help_text='Email of user at time of action (preserved even if user is deleted)'
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True,
        help_text='Type of action performed'
    )
    model_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Name of the model affected'
    )
    object_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text='Primary key of the object affected'
    )
    object_repr = models.CharField(
        max_length=255,
        help_text='String representation of the object'
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dictionary of field changes: {field: {old: value, new: value}}'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the request'
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text='User agent of the request'
    )
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional context data'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When the action occurred'
    )

    class Meta:
        verbose_name = 'Registro de Auditoria'
        verbose_name_plural = 'Registros de Auditoria'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', '-timestamp']),
            models.Index(fields=['tenant', 'action']),
            models.Index(fields=['tenant', 'model_name']),
            models.Index(fields=['tenant', 'user']),
        ]

    def __str__(self):
        return f"{self.user_email} - {self.get_action_display()} - {self.model_name} ({self.timestamp})"

    @classmethod
    def log(cls, tenant, user, action, model_name, object_id=None, object_repr='',
            changes=None, ip_address=None, user_agent=None, extra_data=None):
        """
        Helper method to create an audit log entry.
        """
        return cls.objects.create(
            tenant=tenant,
            user=user,
            user_email=user.email if user else 'system@crediflux.app',
            action=action,
            model_name=model_name,
            object_id=str(object_id) if object_id else None,
            object_repr=object_repr[:255],
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data or {},
        )
