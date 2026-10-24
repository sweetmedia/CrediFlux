"""
Loans app configuration
"""
from django.apps import AppConfig


class LoansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.loans'
    verbose_name = 'Loan Management'

    def ready(self):
        import apps.loans.signals  # noqa: F401

        self._harden_reportlab()

    @staticmethod
    def _harden_reportlab():
        """Ningún recurso `file:`/remoto desde el markup de reportlab (`<img src=...>`).

        Se fija al arrancar porque reportlab memoriza estos valores en el primer
        `open_for_read` (recibos/estados de `reports.py` pueden llegar antes que
        `utils_pdf`). Sólo afecta a URLs: las rutas locales simples se abren igual, y
        `trustedHosts = []` bloquea http/https sólo de forma incidental (la lista no
        tiene `.match`). El control real es escapar el texto de usuario en `utils_pdf`.
        """
        from reportlab import rl_config

        rl_config.trustedSchemes = []
        rl_config.trustedHosts = []
