from django.db import migrations, models


class Migration(migrations.Migration):
    """Red del registro de autoservicio: presupuesto diario de altas y pendientes por red."""

    dependencies = [
        ("tenants", "0019_tenant_provisioning_pending"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="registration_network",
            field=models.CharField(
                blank=True,
                default="",
                max_length=64,
                help_text="Red del registro de autoservicio (IPv4 o IPv6 /48): presupuesto diario de "
                          "altas y pendientes por red",
            ),
        ),
        migrations.AddIndex(
            model_name="tenant",
            index=models.Index(fields=["registration_network", "created_on"], name="tenants_regnet_created_idx"),
        ),
    ]
