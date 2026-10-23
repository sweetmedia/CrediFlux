# Escrita a mano: NexConnect como proveedor e-CF (y el default).
# Solo cambia estado (choices/default/help_text): no genera SQL.
#
# Depende de 0010 a propósito: 0011 (campos AI) existe solo sin trackear en el
# checkout principal. Cuando se commitee, `makemigrations tenants --merge`.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0010_fix_ecf_nullable"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tenant",
            name="ecf_provider",
            field=models.CharField(
                choices=[
                    ("nexconnect", "NexConnect (PSFE)"),
                    ("none", "Sin facturación electrónica"),
                    ("direct", "DGII Directo (certificado propio)"),
                    ("dgmax", "DGMax.do (PSFE)"),
                    ("ef2", "EF2.do (PSFE)"),
                ],
                default="nexconnect",
                help_text="Proveedor de facturación electrónica",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="tenant",
            name="ecf_provider_api_key",
            field=models.CharField(
                blank=True,
                help_text="API Key del proveedor PSFE. NexConnect: key de emisor nxc_…, guardada cifrada",
                max_length=255,
                null=True,
            ),
        ),
    ]
