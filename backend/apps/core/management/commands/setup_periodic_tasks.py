# -*- coding: utf-8 -*-
"""
Management command to setup periodic tasks for django-celery-beat
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Setup periodic tasks in django-celery-beat'

    def handle(self, *args, **options):
        self.stdout.write('Setting up periodic tasks...\n')

        # Create or get the crontab schedule for weekly RNC update
        # Every Sunday at 3:00 AM
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='3',
            day_of_week='0',  # Sunday
            day_of_month='*',
            month_of_year='*',
            timezone='America/Santo_Domingo'
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created crontab schedule: Weekly (Sunday 3:00 AM)')
            )
        else:
            self.stdout.write(
                self.style.WARNING('  Schedule already exists: Weekly (Sunday 3:00 AM)')
            )

        # Create or update the periodic task for RNC database update
        task, created = PeriodicTask.objects.get_or_create(
            name='Update RNC Database from DGII',
            defaults={
                'task': 'apps.core.tasks.update_rnc_database',
                'crontab': schedule,
                'enabled': True,
                'description': 'Actualiza la base de datos de RNC/Cédula desde los archivos públicos de DGII',
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Created periodic task: Update RNC Database from DGII')
            )
        else:
            # Update existing task
            task.crontab = schedule
            task.task = 'apps.core.tasks.update_rnc_database'
            task.enabled = True
            task.description = 'Actualiza la base de datos de RNC/Cédula desde los archivos públicos de DGII'
            task.save()
            self.stdout.write(
                self.style.WARNING('  Updated existing task: Update RNC Database from DGII')
            )

        # Daily late-fee calculation (mora) — 00:30 Santo Domingo
        daily_schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='30',
            hour='0',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='America/Santo_Domingo'
        )
        late_fee_task, created = PeriodicTask.objects.update_or_create(
            name='Calculate late fees (mora)',
            defaults={
                'task': 'loans.calculate_late_fees',
                'crontab': daily_schedule,
                'enabled': True,
                'description': 'Recalcula la mora de las cuotas vencidas en todos los tenants (diario 00:30)',
            }
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ {"Created" if created else "Updated"} periodic task: {late_fee_task.name} (daily 00:30)'
            )
        )

        # WhatsApp: recordatorios de pago (09:00) y avisos de mora (09:30), Santo Domingo.
        # Sólo envían en tenants con enable_whatsapp_reminders y WhatsApp configurado.
        for task_name, label, minute, hour, description in [
            ('loans.send_payment_reminders', 'WhatsApp payment reminders', '0', '9',
             'Recordatorios de cuota por WhatsApp (antes, el día y después del vencimiento)'),
            ('loans.send_overdue_notice', 'WhatsApp overdue notices', '30', '9',
             'Avisos de mora por WhatsApp a los 15, 30, 60 y 90 días de atraso'),
        ]:
            wa_schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_week='*',
                day_of_month='*',
                month_of_year='*',
                timezone='America/Santo_Domingo'
            )
            wa_task, created = PeriodicTask.objects.update_or_create(
                name=label,
                defaults={
                    'task': task_name,
                    'crontab': wa_schedule,
                    'enabled': True,
                    'description': description,
                }
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ {"Created" if created else "Updated"} periodic task: {wa_task.name} (daily {hour}:{minute.zfill(2)})'
                )
            )

        # Show summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Periodic Tasks Summary:')
        self.stdout.write('='*60)
        self.stdout.write(f'Task Name: {task.name}')
        self.stdout.write(f'Task: {task.task}')
        self.stdout.write(f'Schedule: Every Sunday at 3:00 AM (Santo Domingo time)')
        self.stdout.write(f'Enabled: {task.enabled}')
        self.stdout.write(f'Description: {task.description}')
        self.stdout.write('='*60)
        self.stdout.write('\n✓ Periodic tasks setup completed!')
        self.stdout.write(
            self.style.SUCCESS(
                '\nYou can now manage this task from the Django Admin:\n'
                'Admin → Periodic Tasks → Update RNC Database from DGII\n'
            )
        )
