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
