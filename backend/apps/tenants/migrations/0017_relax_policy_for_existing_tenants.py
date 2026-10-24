"""Los tenants existentes conservan su comportamiento previo al desplegar la política.

Hasta la remediación de seguridad la política de préstamos del tenant no se aplicaba en
el backend. Ahora sí (apps/loans/policy.py), y los defaults del modelo son estrictos
(DOP 50,000 máx., 36 % anual, cédula y aprobación de desembolso obligatorias). Para que
el despliegue no rompa la originación de préstamos de los tenants que nunca tocaron su
política, a TODOS los tenants que existen al migrar se les ponen valores permisivos
(equivalentes a "sin política"). Los tenants nuevos siguen con los defaults del modelo.
Cada tenant debe revisar y endurecer su política en Configuración.

Reverse: no-op (no se puede saber qué valores eran elegidos y cuáles defaults).
"""
import logging
from decimal import Decimal

from django.db import migrations

logger = logging.getLogger(__name__)

PERMISSIVE_POLICY = {
    'min_loan_amount': Decimal('0.00'),
    'max_loan_amount': Decimal('100000000.00'),
    'min_interest_rate': Decimal('0.00'),
    'max_interest_rate': Decimal('600.00'),
    'min_loan_term_months': 1,
    'max_loan_term_months': 600,
    'max_active_loans_per_customer': 99,
    'require_id_document': False,
    'require_guarantor': False,
    'require_collateral_default': False,
    'require_credit_score': False,
    'require_disbursement_approval': False,
}


def relax_policy_for_existing_tenants(apps, schema_editor):
    Tenant = apps.get_model('tenants', 'Tenant')
    # Sólo el importe: la columna *_currency de cada MoneyField se conserva.
    for pk, schema_name in Tenant.objects.order_by('pk').values_list('pk', 'schema_name'):
        Tenant.objects.filter(pk=pk).update(**PERMISSIVE_POLICY)
        logger.info(
            'Política de préstamos del tenant %s relajada para conservar su comportamiento '
            'previo; revisarla en Configuración.', schema_name,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0016_alter_tenant_logo'),
    ]

    operations = [
        migrations.RunPython(relax_policy_for_existing_tenants, migrations.RunPython.noop),
    ]
