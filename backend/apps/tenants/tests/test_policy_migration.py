"""Migración 0017: los tenants existentes conservan su comportamiento previo al desplegar
la aplicación de la política de préstamos; los nuevos usan los defaults estrictos."""
import logging
from decimal import Decimal
from importlib import import_module

import pytest

from apps.tenants.models import Tenant

pytestmark = pytest.mark.django_db

MIGRATION = "apps.tenants.migrations.0017_relax_policy_for_existing_tenants"

RELAXED = {
    "min_interest_rate": Decimal("0.00"),
    "max_interest_rate": Decimal("600.00"),
    "min_loan_term_months": 1,
    "max_loan_term_months": 600,
    "max_active_loans_per_customer": 99,
    "require_id_document": False,
    "require_guarantor": False,
    "require_collateral_default": False,
    "require_credit_score": False,
    "require_disbursement_approval": False,
}


def _tenant(schema, **extra):
    return Tenant(schema_name=schema, name=schema, business_name=schema,
                  email=f"{schema}@crediflux.test", **extra)


def test_existing_tenants_get_permissive_policy_and_new_ones_keep_defaults(public_schema, caplog):
    from django.apps import apps as django_apps

    migration = import_module(MIGRATION)
    existing = Tenant.objects.bulk_create([
        _tenant("pol_viejo"),
        _tenant("pol_editado", require_guarantor=True, max_interest_rate=Decimal("48.00")),
    ])

    with caplog.at_level(logging.INFO, logger=MIGRATION):
        migration.relax_policy_for_existing_tenants(django_apps, None)
    migration.relax_policy_for_existing_tenants(django_apps, None)  # idempotente

    for tenant in Tenant.objects.filter(pk__in=[t.pk for t in existing]):
        for field, value in RELAXED.items():
            assert getattr(tenant, field) == value, (tenant.schema_name, field)
        assert tenant.min_loan_amount.amount == Decimal("0.00")
        assert tenant.max_loan_amount.amount == Decimal("100000000.00")
        assert str(tenant.max_loan_amount.currency) == "DOP"

    logged = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
    assert any("pol_viejo" in m for m in logged)
    assert any("pol_editado" in m for m in logged)

    # Tenant creado después de la migración: defaults estrictos del modelo.
    Tenant.objects.bulk_create([_tenant("pol_nuevo")])  # bulk_create: sin CREATE SCHEMA
    nuevo = Tenant.objects.get(schema_name="pol_nuevo")
    assert nuevo.max_interest_rate == Decimal("36.00")
    assert nuevo.max_loan_amount.amount == Decimal("50000.00")
    assert nuevo.require_id_document is True
    assert nuevo.require_disbursement_approval is True
    assert nuevo.max_active_loans_per_customer == 3


def test_reverse_is_noop():
    from django.db import migrations

    migration = import_module(MIGRATION)
    op = migration.Migration.operations[0]
    assert isinstance(op, migrations.RunPython)
    assert op.reverse_code is migrations.RunPython.noop
