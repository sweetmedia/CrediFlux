"""Autorizadores de reversos de pago (Task 14).

Un autorizador es un usuario activo de la financiera del request que es su dueño o tiene el rol
`admin`, con 2FA activa y secreto TOTP. Nunca un usuario de otra financiera: el filtro sale del
tenant del host (`request.tenant`), que `TenantMatches` ya ató al del usuario autenticado.
"""
from django.db.models import Q

from .models import User


def authorizers_queryset(request):
    tenant = getattr(request, 'tenant', None)
    if tenant is None or getattr(tenant, 'schema_name', 'public') == 'public':
        return User.objects.none()
    return (
        User.objects.filter(tenant_id=tenant.pk, is_active=True, is_2fa_enabled=True)
        .filter(Q(is_tenant_owner=True) | Q(role='admin'))
        .exclude(totp_secret__isnull=True)
        .exclude(totp_secret='')
    )


def authorizer_or_none(request, authorizer_id):
    """El autorizador con ese id si es válido para este request; si no (o el id no sirve), None."""
    try:
        pk = int(str(authorizer_id).strip())
    except (TypeError, ValueError):
        return None
    return authorizers_queryset(request).filter(pk=pk).first()


def role_label(user):
    return 'Dueño' if user.is_tenant_owner else user.get_role_display()
