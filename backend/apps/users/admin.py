"""
User admin configuration with Unfold best practices
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.crypto import get_random_string
from unfold.admin import ModelAdmin
from unfold.decorators import display, action
from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
from rest_framework import serializers
from .lockout import validate_strength
from .models import User
from .tokens import revoke_user_credentials

# Campos que sólo el superusuario de plataforma (tenant=None) puede ver o editar.
PRIVILEGE_FIELDS = ('is_superuser', 'is_staff', 'groups', 'user_permissions', 'tenant', 'is_tenant_owner')


def _is_platform_admin(user):
    return user.is_superuser and user.tenant_id is None


def _strength_errors(password, user):
    """Mensajes de los validadores de fortaleza (lista vacía si la contraseña es válida)."""
    try:
        validate_strength(password, user=user)
    except serializers.ValidationError as exc:
        return [str(error) for error in exc.detail]
    return []


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """Admin interface for User model with Unfold best practices"""

    # Unfold specific settings
    list_fullwidth = True
    warn_unsaved_form = True
    compressed_fields = True

    # List view configuration
    list_display = [
        'email', 'show_email_verified', 'first_name', 'last_name', 'show_tenant',
        'show_role', 'show_owner', 'show_active', 'created_at'
    ]
    list_filter = ['is_active', 'role', 'is_tenant_owner', 'tenant', 'email_verified', 'created_at', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'username', 'tenant__name', 'tenant__business_name']
    ordering = ['-created_at']
    list_per_page = 25

    @display(description="Tenant", label=True)
    def show_tenant(self, obj):
        """Display tenant with color badge"""
        if obj.tenant:
            return 'info', obj.tenant.business_name or obj.tenant.name
        return 'secondary', 'System Admin'

    @display(description="Role", label=True)
    def show_role(self, obj):
        """Display role with color badge"""
        colors = {
            'admin': 'danger',
            'manager': 'warning',
            'loan_officer': 'info',
            'collector': 'info',
            'collection_supervisor': 'warning',
            'accountant': 'info',
            'cashier': 'success',
            'viewer': 'secondary',
        }
        return colors.get(obj.role, 'info'), obj.get_role_display()

    @display(description="Owner", label={True: "success", False: "secondary"})
    def show_owner(self, obj):
        """Display if user is tenant owner"""
        if obj.is_tenant_owner:
            return True, 'Owner'
        return False, 'Staff'

    @display(description="Active", label=True)
    def show_active(self, obj):
        """Display active status with color badge"""
        if obj.is_active:
            return 'success', 'Active'
        return 'danger', 'Inactive'

    @display(description="Email Verified", label=True)
    def show_email_verified(self, obj):
        """Display email verification status with color badge"""
        try:
            email_address = EmailAddress.objects.get(user=obj, email=obj.email)
            if email_address.verified:
                return 'success', '✓ Verificado'
            return 'warning', '⏳ Pendiente'
        except EmailAddress.DoesNotExist:
            return 'danger', '✗ Sin verificar'

    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'email', 'password')
        }),
        ('Tenant Association', {
            'fields': ('tenant', 'is_tenant_owner'),
            'description': 'Tenant this user belongs to. Leave empty for system administrators.'
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone', 'avatar', 'bio')
        }),
        ('Professional Information', {
            'fields': ('job_title', 'department', 'role')
        }),
        ('Collection Settings', {
            'fields': ('collection_zone', 'daily_collection_target'),
            'classes': ('collapse',),
            'description': 'Only applicable for collectors and collection supervisors.'
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Two-Factor Authentication', {
            'fields': ('is_2fa_enabled',),
            'classes': ('collapse',),
            'description': 'Manage 2FA settings. Users configure TOTP via their profile.'
        }),
        ('Settings', {
            'fields': ('email_verified', 'receive_notifications')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'last_login_at', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'tenant', 'is_tenant_owner', 'password1', 'password2', 'role'),
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login', 'date_joined']
    actions = [
        'reset_password_action',
        'activate_users',
        'deactivate_users',
        'resend_verification_email',
    ]

    # ------------------------------------------------------------------
    # Custom URLs for password reset form
    # ------------------------------------------------------------------

    def get_urls(self):
        """Add custom URL for password reset confirmation"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:user_id>/reset-password/',
                self.admin_site.admin_view(self.reset_password_view),
                name='users_user_reset_password',
            ),
        ]
        return custom_urls + urls

    def reset_password_view(self, request, user_id):
        """View to reset a specific user's password with a form"""
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
            return redirect(reverse('admin:users_user_changelist'))

        if not self._can_reset(request, user):
            raise PermissionDenied

        if request.method == 'POST':
            new_password = request.POST.get('new_password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()
            generate_random = request.POST.get('generate_random') == 'true'

            if generate_random:
                new_password = get_random_string(12, 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#$%')
                user.set_password(new_password)
                user.save()
                revoke_user_credentials(user)
                messages.success(
                    request,
                    f'✅ Contraseña de {user.email} reseteada. '
                    f'Nueva contraseña: {new_password} — Compártela de forma segura.'
                )
                return redirect(reverse('admin:users_user_changelist'))

            if not new_password:
                messages.error(request, 'La contraseña no puede estar vacía.')
            elif new_password != confirm_password:
                messages.error(request, 'Las contraseñas no coinciden.')
            elif password_errors := _strength_errors(new_password, user):
                for error in password_errors:
                    messages.error(request, error)
            else:
                user.set_password(new_password)
                user.save()
                revoke_user_credentials(user)
                messages.success(
                    request,
                    f'✅ Contraseña de {user.email} actualizada exitosamente.'
                )
                return redirect(reverse('admin:users_user_changelist'))

            # On error, fall through to render form again

        context = {
            **self.admin_site.each_context(request),
            'title': f'Reset Password — {user.get_full_name()}',
            'user_obj': user,
            'opts': self.model._meta,
        }
        return render(request, 'admin/users/reset_password.html', context)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    @staticmethod
    def _can_reset(request, target):
        """Superusuario de plataforma, o gestor de usuarios del mismo tenant sobre un no-superusuario."""
        actor = request.user
        if _is_platform_admin(actor):
            return True
        return (
            actor.can_manage_users()
            and actor.tenant_id is not None
            and target.tenant_id == actor.tenant_id
            and not target.is_superuser
        )

    @action(description="🔑 Resetear contraseña", permissions=['change'])
    def reset_password_action(self, request, queryset):
        """
        Bulk action: If single user selected, redirect to reset form.
        If multiple, generate random passwords for all.
        """
        if queryset.count() == 1:
            user = queryset.first()
            return redirect(
                reverse('admin:users_user_reset_password', args=[user.pk])
            )

        # Multiple users: generate random passwords
        results = []
        for user in queryset:
            if not self._can_reset(request, user):
                messages.error(request, f'No tienes permiso para resetear la contraseña de {user.email}.')
                continue
            new_password = get_random_string(12, 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#$%')
            user.set_password(new_password)
            user.save()
            revoke_user_credentials(user)
            results.append(f'{user.email}: {new_password}')

        self.message_user(
            request,
            f'🔑 Contraseñas reseteadas para {len(results)} usuario(s). '
            f'Revisa los logs o comparte las credenciales de forma segura.',
            level=messages.SUCCESS
        )

        # Log the passwords (they show in the Django messages, visible only to the admin)
        for result in results:
            self.message_user(request, f'  → {result}', level=messages.INFO)

    @action(description="✅ Activar usuarios seleccionados", permissions=['change'])
    def activate_users(self, request, queryset):
        """Activate selected users"""
        count = queryset.filter(is_active=False).update(is_active=True)
        if count:
            self.message_user(
                request,
                f'✅ {count} usuario(s) activado(s) exitosamente.',
                level=messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'Todos los usuarios seleccionados ya están activos.',
                level=messages.INFO
            )

    @action(description="🚫 Desactivar usuarios seleccionados", permissions=['change'])
    def deactivate_users(self, request, queryset):
        """Deactivate selected users (excluding yourself and tenant owners)"""
        # Exclude current user and tenant owners from deactivation
        safe_qs = queryset.exclude(pk=request.user.pk).exclude(is_tenant_owner=True)
        skipped = queryset.count() - safe_qs.count()
        count = safe_qs.filter(is_active=True).update(is_active=False)

        if count:
            self.message_user(
                request,
                f'🚫 {count} usuario(s) desactivado(s) exitosamente.',
                level=messages.SUCCESS
            )
        if skipped:
            self.message_user(
                request,
                f'⚠️ {skipped} usuario(s) omitido(s) (tu cuenta o tenant owners no se pueden desactivar).',
                level=messages.WARNING
            )

    @action(description="📧 Reenviar email de verificación", permissions=['change'])
    def resend_verification_email(self, request, queryset):
        """
        Admin action to resend email verification to selected users.
        Only sends to users who have not verified their email.
        """
        sent_count = 0
        already_verified = 0
        error_count = 0

        for user in queryset:
            try:
                email_address = EmailAddress.objects.get(user=user, email=user.email)

                if email_address.verified:
                    already_verified += 1
                    continue

                send_email_confirmation(request, user)
                sent_count += 1

            except EmailAddress.DoesNotExist:
                try:
                    EmailAddress.objects.create(
                        user=user,
                        email=user.email,
                        primary=True,
                        verified=False
                    )
                    send_email_confirmation(request, user)
                    sent_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(
                        request,
                        f"Error al procesar {user.email}: {str(e)}",
                        level=messages.ERROR
                    )
            except Exception as e:
                error_count += 1
                self.message_user(
                    request,
                    f"Error al enviar email a {user.email}: {str(e)}",
                    level=messages.ERROR
                )

        if sent_count > 0:
            self.message_user(
                request,
                f"📧 Se enviaron {sent_count} email(s) de verificación exitosamente.",
                level=messages.SUCCESS
            )

        if already_verified > 0:
            self.message_user(
                request,
                f"{already_verified} usuario(s) ya tienen su email verificado.",
                level=messages.INFO
            )

        if error_count > 0:
            self.message_user(
                request,
                f"Ocurrieron {error_count} error(es) al procesar algunos usuarios.",
                level=messages.WARNING
            )

    # ------------------------------------------------------------------
    # Queryset & Permissions
    # ------------------------------------------------------------------

    def get_queryset(self, request):
        """
        Filter users based on tenant ownership.
        - Superusers see all users
        - Tenant owners/admins see only users from their tenant
        """
        qs = super().get_queryset(request)

        if request.user.is_superuser and request.user.tenant is None:
            return qs

        if request.user.tenant:
            return qs.filter(tenant=request.user.tenant)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Limit tenant selection based on user permissions.
        """
        if db_field.name == "tenant":
            if request.user.is_superuser and request.user.tenant is None:
                pass
            elif request.user.tenant:
                kwargs["queryset"] = request.user.tenant.__class__.objects.filter(pk=request.user.tenant.pk)
            else:
                kwargs["queryset"] = db_field.related_model.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.can_manage_users()

    def has_change_permission(self, request, obj=None):
        if _is_platform_admin(request.user):
            return True
        if obj and request.user.tenant:
            return (
                obj.tenant_id == request.user.tenant_id
                and not obj.is_superuser
                and request.user.can_manage_users()
            )
        return request.user.can_manage_users()

    def has_delete_permission(self, request, obj=None):
        if _is_platform_admin(request.user):
            return True
        if obj and request.user.tenant:
            return self.has_change_permission(request, obj) and not obj.is_tenant_owner
        return False

    # ------------------------------------------------------------------
    # Privilege fields: only the platform superuser sees or edits them
    # ------------------------------------------------------------------

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if _is_platform_admin(request.user):
            return fieldsets
        stripped = []
        for name, options in fieldsets:
            fields = tuple(f for f in options['fields'] if f not in PRIVILEGE_FIELDS)
            if fields:
                stripped.append((name, {**options, 'fields': fields}))
        return stripped

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not _is_platform_admin(request.user):
            readonly += [f for f in PRIVILEGE_FIELDS if f not in readonly]
        return readonly

    def save_model(self, request, obj, form, change):
        # `tenant` es read-only para el admin de tenant: los usuarios que crea quedan en su tenant.
        if not change and not _is_platform_admin(request.user):
            obj.tenant_id = request.user.tenant_id
        super().save_model(request, obj, form, change)
