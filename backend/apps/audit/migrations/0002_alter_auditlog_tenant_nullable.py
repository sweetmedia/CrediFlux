# AuditLog.tenant admite NULL: filas de plataforma, p. ej. la traza del borrado de un tenant.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0001_initial"),
        ("tenants", "0006_tenant_imap_host_tenant_imap_password_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditlog",
            name="tenant",
            field=models.ForeignKey(
                blank=True,
                help_text="Tenant to which this log belongs (vacío = registro de plataforma, p. ej. el borrado de un tenant)",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="audit_logs",
                to="tenants.tenant",
            ),
        ),
    ]
