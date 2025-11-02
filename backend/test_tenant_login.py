#!/usr/bin/env python
"""
Test script to verify tenant-aware login validation.
Run: docker-compose exec backend python test_tenant_login.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant
from apps.users.serializers import TenantAwareLoginSerializer
from unittest.mock import Mock
from rest_framework.exceptions import ValidationError

User = get_user_model()

print("\n" + "="*60)
print("TESTING TENANT-AWARE LOGIN VALIDATION")
print("="*60 + "\n")

# Get two different tenants
try:
    tenant1 = Tenant.objects.filter(schema_name__in=['caproinsa', 'amsfin']).first()
    tenant2 = Tenant.objects.exclude(id=tenant1.id).filter(schema_name__in=['caproinsa', 'amsfin']).first()

    if not tenant1 or not tenant2:
        print("❌ ERROR: Need at least 2 tenants (caproinsa and amsfin) to test")
        print("Available tenants:", list(Tenant.objects.values_list('schema_name', flat=True)))
        exit(1)

    print(f"✅ Found tenants:")
    print(f"   - Tenant 1: {tenant1.schema_name} (ID: {tenant1.id})")
    print(f"   - Tenant 2: {tenant2.schema_name} (ID: {tenant2.id})")
    print()

    # Get a user from tenant1
    user = User.objects.filter(tenant=tenant1, is_active=True).first()
    if not user:
        print(f"❌ ERROR: No active users found for tenant {tenant1.schema_name}")
        exit(1)

    print(f"✅ Test user: {user.email} (belongs to {tenant1.schema_name})")
    print()

    # Test 1: User tries to login to their own tenant (should SUCCEED)
    print("TEST 1: Login to CORRECT tenant")
    print(f"   User: {user.email} (from {tenant1.schema_name})")
    print(f"   Logging into: {tenant1.schema_name}")

    mock_request = Mock()
    mock_request.tenant = tenant1

    serializer = TenantAwareLoginSerializer(context={'request': mock_request})
    attrs = {'user': user}

    try:
        result = serializer.validate(attrs)
        print(f"   ✅ SUCCESS: Login allowed (as expected)")
    except ValidationError as e:
        print(f"   ❌ FAILED: Login blocked (unexpected!)")
        print(f"   Error: {e}")
    print()

    # Test 2: User tries to login to different tenant (should FAIL)
    print("TEST 2: Login to WRONG tenant (cross-tenant attack)")
    print(f"   User: {user.email} (from {tenant1.schema_name})")
    print(f"   Trying to login to: {tenant2.schema_name}")

    mock_request2 = Mock()
    mock_request2.tenant = tenant2

    serializer2 = TenantAwareLoginSerializer(context={'request': mock_request2})
    attrs2 = {'user': user}

    try:
        result = serializer2.validate(attrs2)
        print(f"   ❌ FAILED: Login allowed (SECURITY BREACH!)")
        print(f"   This user should NOT be able to login to {tenant2.schema_name}")
    except ValidationError as e:
        print(f"   ✅ SUCCESS: Login blocked (as expected)")
        print(f"   Error message: {str(e.detail[0])}")
    print()

    # Test 3: System admin (no tenant) can access any tenant
    superuser = User.objects.filter(is_superuser=True, tenant__isnull=True).first()
    if superuser:
        print("TEST 3: System admin login to any tenant")
        print(f"   User: {superuser.email} (System Admin)")
        print(f"   Trying to login to: {tenant1.schema_name}")

        mock_request3 = Mock()
        mock_request3.tenant = tenant1

        serializer3 = TenantAwareLoginSerializer(context={'request': mock_request3})
        attrs3 = {'user': superuser}

        try:
            result = serializer3.validate(attrs3)
            print(f"   ✅ SUCCESS: System admin can access any tenant (as expected)")
        except ValidationError as e:
            print(f"   ❌ FAILED: System admin blocked (unexpected!)")
            print(f"   Error: {e}")
    else:
        print("TEST 3: SKIPPED (no system admin users found)")

    print()
    print("="*60)
    print("TESTING COMPLETE")
    print("="*60)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
