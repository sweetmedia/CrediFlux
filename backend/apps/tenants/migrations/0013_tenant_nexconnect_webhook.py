# Escrita a mano: webhook de NexConnect por tenant (id + secret HMAC cifrado).
#
# Depende de 0012 (que a su vez salta la 0011 sin trackear del checkout
# principal). Cuando se commitee la 0011, `makemigrations tenants --merge`.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0012_ecf_provider_nexconnect"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="nexconnect_webhook_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Id del webhook registrado en NexConnect (POST /v1/webhooks/)",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="nexconnect_webhook_secret",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Secret HMAC del webhook de NexConnect, guardado cifrado",
                max_length=255,
            ),
        ),
    ]
