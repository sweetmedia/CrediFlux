"""Crea los 8 roles de sistema de cada financiera existente (D6). Idempotente."""
from django.db import migrations


def crear_roles(apps, schema_editor):
    from apps.users.models_roles import crear_roles_de_sistema_para_todos

    crear_roles_de_sistema_para_todos(apps.get_model('tenants', 'Tenant'), apps.get_model('users', 'Role'))


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_role'),
    ]

    operations = [
        # Sin reverso propio: deshacer 0009 borra la tabla con sus filas.
        migrations.RunPython(crear_roles, migrations.RunPython.noop),
    ]
