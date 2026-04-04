"""
Fix NOT NULL constraints on e-CF fields.

On VPN3 production, a different migration branch (0009_tenant_dgii_environment...)
created ecf_provider_api_key and ecf_provider_api_secret as NOT NULL.
The canonical model defines them as null=True, blank=True.

This migration ensures the DB constraint matches the model.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0009_add_ecf_fields"),
    ]

    operations = [
        # Force DB columns to accept NULL (idempotent — safe if already nullable)
        migrations.RunSQL(
            sql=[
                "ALTER TABLE tenants ALTER COLUMN ecf_provider_api_key DROP NOT NULL;",
                "ALTER TABLE tenants ALTER COLUMN ecf_provider_api_secret DROP NOT NULL;",
            ],
            reverse_sql=[
                "ALTER TABLE tenants ALTER COLUMN ecf_provider_api_key SET NOT NULL;",
                "ALTER TABLE tenants ALTER COLUMN ecf_provider_api_secret SET NOT NULL;",
            ],
        ),
        # Sync Django's migration state with the model definition
        migrations.AlterField(
            model_name="tenant",
            name="ecf_provider_api_key",
            field=models.CharField(
                max_length=255,
                blank=True,
                null=True,
                help_text="API Key del proveedor PSFE (DGMax/EF2)",
            ),
        ),
        migrations.AlterField(
            model_name="tenant",
            name="ecf_provider_api_secret",
            field=models.CharField(
                max_length=255,
                blank=True,
                null=True,
                help_text="API Secret del proveedor PSFE (DGMax/EF2)",
            ),
        ),
    ]
