"""Formulario de login del admin de Django con segundo factor.

El admin estándar sólo pide contraseña. Para usuarios con 2FA activo este formulario
exige además un código TOTP o de respaldo, con el mismo contador de intentos que la
puerta JWT (`lockout.check_and_count_2fa`). Lo instala `lockout.ratelimit_admin_login`.
"""
from django import forms
from rest_framework import serializers
from unfold.forms import AuthenticationForm

from . import lockout


class TwoFactorAdminAuthenticationForm(AuthenticationForm):
    otp = forms.CharField(
        required=False,
        max_length=16,
        label='Código 2FA',
        help_text='Sólo si tienes la verificación en dos pasos activa: código de la app o de respaldo.',
        widget=forms.TextInput(attrs={'autocomplete': 'one-time-code'}),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields['otp'].widget.attrs['class'] = self.fields['password'].widget.attrs.get('class', '')

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_2fa_enabled:
            return

        from .backup_codes import consume_backup_code
        from .totp import verify_totp_once

        code = (self.cleaned_data.get('otp') or '').strip()
        if not code:
            raise forms.ValidationError('Introduce tu código de verificación en dos pasos.', code='otp_required')
        try:
            lockout.check_and_count_2fa(user)
        except serializers.ValidationError:
            raise forms.ValidationError(lockout.LOCKOUT_MESSAGE, code='locked')
        if not (verify_totp_once(user, code) or consume_backup_code(user, code)):
            raise forms.ValidationError('Código de verificación inválido.', code='invalid_2fa')
        lockout.reset_2fa(user)
