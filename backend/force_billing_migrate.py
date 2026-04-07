"""
Force billing migration on public schema.
Handles the case where django_migrations says applied but tables don't exist.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db import connection

# Check if billing_invoice table exists
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name LIKE 'billing_%'
    """)
    existing = [row[0] for row in cursor.fetchall()]
    print(f"Existing billing tables: {existing}")

    if not existing:
        print("No billing tables found. Faking back and re-running migration...")
        
        # Delete the billing migration record so it can be re-applied
        cursor.execute("DELETE FROM django_migrations WHERE app = 'billing'")
        print(f"Deleted billing migration records")
        
        # Also delete loans/communications/users migration records if their tables don't exist
        for app in ['loans', 'communications']:
            cursor.execute(f"""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name LIKE '{app}_%'
            """)
            app_tables = [row[0] for row in cursor.fetchall()]
            if not app_tables:
                cursor.execute(f"DELETE FROM django_migrations WHERE app = '{app}'")
                print(f"Deleted {app} migration records (no tables found)")
    else:
        print("Billing tables already exist!")
        
print("\nDone. Now run: python manage.py migrate")
