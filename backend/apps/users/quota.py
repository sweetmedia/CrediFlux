"""Cupo de usuarios activos del plan (Tenant.max_users)."""
from apps.tenants.models import Tenant

SEAT_LIMIT_MESSAGE = 'Límite de usuarios del plan alcanzado.'


def seats_left(tenant_id):
    """Cupos libres del tenant, o None si no hay tenant (superusuario de plataforma).

    Debe llamarse dentro de transaction.atomic(): bloquea la fila del tenant para que dos
    altas o activaciones simultáneas no pasen a la vez el control.
    """
    from .models import User

    if tenant_id is None:
        return None
    tenant = Tenant.objects.select_for_update().get(pk=tenant_id)
    return tenant.max_users - User.objects.filter(tenant_id=tenant_id, is_active=True).count()
