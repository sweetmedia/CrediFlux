#!/usr/bin/env python
"""Setup initial public tenant and domain for CrediFlux."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.tenants.models import Tenant, Domain
from apps.users.models import User

# Create public tenant if it doesn't exist
tenant, created = Tenant.objects.get_or_create(
    schema_name='public',
    defaults={
        'name': 'CrediFlux',
        'business_name': 'CrediFlux Platform',
        'is_active': True,
    }
)
if created:
    print(f"✅ Public tenant created: {tenant.name}")
else:
    print(f"ℹ️  Public tenant already exists: {tenant.name}")

# Create domains for the public tenant
domains_to_create = [
    'localhost',
    '10.0.0.93',
    'sweetmediabox',
    'crediflux.local',
]

for domain_name in domains_to_create:
    domain, created = Domain.objects.get_or_create(
        domain=domain_name,
        defaults={
            'tenant': tenant,
            'is_primary': domain_name == 'localhost',
        }
    )
    if created:
        print(f"✅ Domain created: {domain_name}")
    else:
        print(f"ℹ️  Domain already exists: {domain_name}")

# Create superuser
try:
    if not User.objects.filter(email='admin@crediflux.com').exists():
        user = User.objects.create_superuser(
            email='admin@crediflux.com',
            password='admin2026',
            first_name='Admin',
            last_name='CrediFlux',
        )
        print(f"✅ Superuser created: admin@crediflux.com / admin2026")
    else:
        print(f"ℹ️  Superuser already exists: admin@crediflux.com")
except Exception as e:
    print(f"⚠️  Superuser creation error: {e}")
    # Try with username if email-only doesn't work
    try:
        if not User.objects.filter(username='admin').exists():
            user = User.objects.create_superuser(
                username='admin',
                email='admin@crediflux.com',
                password='admin2026',
            )
            print(f"✅ Superuser created: admin / admin2026")
        else:
            print(f"ℹ️  Superuser already exists: admin")
    except Exception as e2:
        print(f"❌ Superuser creation failed: {e2}")

print("\n🎉 Initial setup complete!")
