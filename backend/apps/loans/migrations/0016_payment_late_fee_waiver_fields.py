# Generated manually for late fee waiver support
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import djmoney.models.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('loans', '0015_alter_collateral_appraisal_value_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='loanschedule',
            name='late_fee_waived',
            field=djmoney.models.fields.MoneyField(decimal_places=2, default=0, default_currency='DOP', help_text='Mora condonada/exonerada', max_digits=14),
        ),
        migrations.AddField(
            model_name='loanpayment',
            name='late_fee_original_amount',
            field=djmoney.models.fields.MoneyField(decimal_places=2, default=0, default_currency='DOP', help_text='Mora original detectada al momento del pago', max_digits=14),
        ),
        migrations.AddField(
            model_name='loanpayment',
            name='late_fee_waived_amount',
            field=djmoney.models.fields.MoneyField(decimal_places=2, default=0, default_currency='DOP', help_text='Monto de mora condonado en este pago', max_digits=14),
        ),
        migrations.AddField(
            model_name='loanpayment',
            name='late_fee_waived_at',
            field=models.DateTimeField(blank=True, help_text='Fecha/hora en que se condonó la mora', null=True),
        ),
        migrations.AddField(
            model_name='loanpayment',
            name='late_fee_waived_by',
            field=models.ForeignKey(blank=True, help_text='Usuario que condonó la mora', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='loan_payments_late_fee_waived', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='loanpayment',
            name='late_fee_waiver_reason',
            field=models.TextField(blank=True, help_text='Motivo de la condonación de mora', null=True),
        ),
    ]
