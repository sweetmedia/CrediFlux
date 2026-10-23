# Escrita a mano: eventos de webhook de NexConnect (idempotencia por evento) y
# la acción 'webhook' en ECFSubmission.
#
# Depende de 0001 a propósito: la 0002 existe solo sin trackear en el checkout
# principal. Cuando se commitee, `makemigrations billing --merge`.

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ecfsubmission",
            name="action",
            field=models.CharField(
                choices=[
                    ("submit", "Envío de e-CF"),
                    ("query_status", "Consulta de Estado"),
                    ("query_result", "Consulta de Resultado"),
                    ("cancel", "Anulación"),
                    ("webhook", "Webhook del proveedor"),
                ],
                help_text="Tipo de acción realizada",
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="NexConnectWebhookEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("event_id", models.CharField(help_text="Id del evento (evt_…)", max_length=100, unique=True)),
                ("event_type", models.CharField(help_text="Tipo de evento (invoice.accepted, …)", max_length=60)),
                ("event_created_at", models.DateTimeField(blank=True, help_text="Fecha del evento según NexConnect", null=True)),
                ("nexconnect_invoice_id", models.CharField(blank=True, help_text="Id de la factura en NexConnect", max_length=64)),
                ("outcome", models.CharField(
                    choices=[
                        ("applied", "Aplicado"),
                        ("stale", "Ignorado (más viejo que el estado actual)"),
                        ("unmatched", "Sin factura asociada"),
                        ("mismatch", "Factura con otro id de NexConnect"),
                        ("ignored", "Tipo de evento no manejado"),
                    ],
                    max_length=20,
                )),
                ("payload", models.JSONField(blank=True, help_text="Evento recibido (sin XML ni líneas)", null=True)),
                ("invoice", models.ForeignKey(
                    blank=True, help_text="Factura afectada", null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="nexconnect_events", to="billing.invoice",
                )),
            ],
            options={
                "verbose_name": "Evento de webhook NexConnect",
                "verbose_name_plural": "Eventos de webhook NexConnect",
                "ordering": ["-created_at"],
            },
        ),
    ]
