from django.db import migrations, models


class Migration(migrations.Migration):
    """Registros de autoservicio por encima del tope diario: quedan pendientes, sin schema."""

    dependencies = [
        ("tenants", "0018_merge_20261024_1745"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="provisioning_pending",
            field=models.BooleanField(
                default=False,
                help_text="Registro de autoservicio recibido por encima del tope diario: sin schema "
                          "hasta que un superusuario lo aprovisione",
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="pending_since",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Momento en que el registro quedó pendiente de aprovisionamiento",
            ),
        ),
    ]
