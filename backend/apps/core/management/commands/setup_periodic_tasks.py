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

        # Tareas diarias por tenant. Beat las dispara CADA HORA y cada tarea procesa
        # sólo los tenants donde ahora es la hora local que le toca (Tenant.timezone):
        # mora 00:30, recordatorios WhatsApp 09:00, avisos de mora 09:30.
        for task_name, label, minute, description in [
            ('loans.calculate_late_fees', 'Calculate late fees (mora)', '30',
             'Recalcula la mora a las 00:30 locales de cada tenant'),
            ('loans.send_payment_reminders', 'WhatsApp payment reminders', '0',
             'Recordatorios de cuota por WhatsApp a las 09:00 locales de cada tenant'),
            ('loans.send_overdue_notice', 'WhatsApp overdue notices', '30',
             'Avisos de mora por WhatsApp (15/30/60/90 días) a las 09:30 locales de cada tenant'),
            ('communications.sync_whatsapp_templates', 'WhatsApp templates sync', '15',
             'Crea en Meta las plantillas que falten y refresca su estado (cada hora, todas las financieras)'),
        ]:
            hourly, _ = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour='*',
                day_of_week='*',
                day_of_month='*',
                month_of_year='*',
                timezone='UTC'
            )
            periodic, created = PeriodicTask.objects.update_or_create(
                name=label,
                defaults={
                    'task': task_name,
                    'crontab': hourly,
                    'enabled': True,
                    'description': description,
                }
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ {"Created" if created else "Updated"} periodic task: {periodic.name} (hourly at :{minute.zfill(2)})'
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
