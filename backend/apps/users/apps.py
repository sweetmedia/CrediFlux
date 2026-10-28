"""
Users app configuration
"""
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'User Management'

    def ready(self):
        # 2FA obligatoria para dueño y administradores en toda vista de DRF (Task 15).
        from .permissions_2fa import install
        install()
