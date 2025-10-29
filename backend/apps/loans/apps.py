"""
Loans app configuration
"""
from django.apps import AppConfig


class LoansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.loans'
    verbose_name = 'Loan Management'

    def ready(self):
        import apps.loans.signals
