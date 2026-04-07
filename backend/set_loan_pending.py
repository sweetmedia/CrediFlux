"""
Script to set a loan to pending status for testing approval workflow
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.loans.models import Loan
from django_tenants.utils import tenant_context, get_tenant_model

# Get tenant
Tenant = get_tenant_model()

try:
    # Ask for tenant name
    tenant_name = input("Enter tenant schema name (e.g., democompany, testcompany): ").strip()

    try:
        tenant = Tenant.objects.get(schema_name=tenant_name)
    except Tenant.DoesNotExist:
        print(f"❌ Tenant '{tenant_name}' not found")
        print("\nAvailable tenants:")
        for t in Tenant.objects.exclude(schema_name='public'):
            print(f"  - {t.schema_name}")
        exit(1)

    with tenant_context(tenant):
        # Get all loans
        loans = Loan.objects.all()

        if not loans.exists():
            print("❌ No loans found in this tenant")
            exit(1)

        print(f"\n📋 Available loans in {tenant_name}:")
        print(f"{'ID':<38} {'Loan Number':<15} {'Customer':<30} {'Status':<12} {'Amount':<15}")
        print("-" * 110)

        for loan in loans:
            print(f"{loan.id} {loan.loan_number:<15} {loan.customer.get_full_name():<30} {loan.status:<12} ${loan.principal_amount.amount:,.2f}")

        print("\n")
        loan_id = input("Enter the loan ID to set as pending: ").strip()

        try:
            loan = Loan.objects.get(id=loan_id)

            print(f"\n📝 Current loan details:")
            print(f"  Loan Number: {loan.loan_number}")
            print(f"  Customer: {loan.customer.get_full_name()}")
            print(f"  Amount: ${loan.principal_amount.amount:,.2f}")
            print(f"  Current Status: {loan.status}")

            if loan.status == 'pending':
                print(f"\n✅ Loan is already in pending status")
            else:
                confirm = input(f"\nChange status from '{loan.status}' to 'pending'? (y/n): ").strip().lower()

                if confirm == 'y':
                    loan.status = 'pending'
                    loan.approval_date = None
                    loan.approved_by = None
                    loan.rejection_date = None
                    loan.rejected_by = None
                    loan.approval_notes = None
                    loan.save()

                    print(f"\n✅ Loan {loan.loan_number} successfully set to pending status!")
                    print(f"\n💡 Now you can test the approval workflow in the frontend")
                else:
                    print("\n❌ Operation cancelled")

        except Loan.DoesNotExist:
            print(f"❌ Loan with ID '{loan_id}' not found")
        except ValueError:
            print(f"❌ Invalid loan ID format")

except KeyboardInterrupt:
    print("\n\n❌ Operation cancelled by user")
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
