"""
Desactivar un tenant revoca los JWT de todos sus usuarios.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Tenant


@receiver(pre_save, sender=Tenant)
def remember_previous_is_active(sender, instance, **kwargs):
    previous = None
    if instance.pk:
        previous = sender.objects.filter(pk=instance.pk).values_list('is_active', flat=True).first()
    instance._previous_is_active = previous


@receiver(post_save, sender=Tenant)
def revoke_credentials_on_deactivation(sender, instance, created, **kwargs):
    if created or not getattr(instance, '_previous_is_active', None) or instance.is_active:
        return
    from apps.users.tokens import revoke_user_credentials

    for user in instance.users.all():
        revoke_user_credentials(user)
