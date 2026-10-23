"""Campos de serializer propios del módulo de préstamos."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

INVALID_TENANT_USER = 'Usuario no válido para esta organización.'


class TenantUserField(serializers.PrimaryKeyRelatedField):
    """FK a usuario limitada a los usuarios activos del tenant de quien hace la petición.

    La tabla de usuarios es compartida entre tenants (schema public), así que sin
    este filtro se podría asignar un usuario de otra organización. El mismo mensaje
    para inexistente y foráneo evita enumerar usuarios de otros tenants.
    """

    default_error_messages = {
        'does_not_exist': INVALID_TENANT_USER,
        'incorrect_type': INVALID_TENANT_USER,
    }

    def get_queryset(self):
        User = get_user_model()
        request = self.context.get('request')
        tenant_id = getattr(getattr(request, 'user', None), 'tenant_id', None)
        if not tenant_id:
            return User.objects.none()
        return User.objects.filter(tenant_id=tenant_id, is_active=True)
