"""Add e-CF (Facturación Electrónica) fields to Tenant model."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0008_alter_tenant_auto_approval_max_amount_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="ecf_provider",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("none", "Sin facturación electrónica"),
                    ("direct", "DGII Directo (certificado propio)"),
                    ("dgmax", "DGMax.do (PSFE)"),
                    ("ef2", "EF2.do (PSFE)"),
                ],
                default="none",
                help_text="Proveedor de facturación electrónica",
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="dgii_environment",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("testecf", "Pre-Certificación (Pruebas)"),
                    ("certecf", "Certificación"),
                    ("ecf", "Producción"),
                ],
                default="testecf",
                help_text="Ambiente DGII para e-CF",
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="ecf_provider_api_key",
            field=models.CharField(
                max_length=255,
                blank=True,
                null=True,
                help_text="API Key del proveedor PSFE (DGMax/EF2)",
            ),
        ),
        migrations.AddField(
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
