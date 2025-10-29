# Constance Configuration - Dynamic Settings

## Overview

CrediFlux uses Django Constance for dynamic application settings that can be changed without redeploying the application. These settings are stored in the database and can be modified through the Django admin interface.

## Accessing Settings

**Admin URL:** `/admin/constance/config/`

**Permissions:** Only superusers can view and modify these settings.

## Configuration Groups

### 1. Company Information
Settings related to company identity and contact information.

- **COMPANY_NAME**: Company name displayed throughout the application
- **COMPANY_EMAIL**: Primary company email address for notifications and contact
- **COMPANY_PHONE**: Primary company phone number
- **COMPANY_ADDRESS**: Company physical address

### 2. Currency & Financial
Currency display and formatting settings.

- **DEFAULT_CURRENCY**: Default currency code (ISO 4217 format, e.g., USD, EUR)
- **CURRENCY_SYMBOL**: Currency symbol to display (e.g., $, €, £)
- **DECIMAL_PLACES**: Number of decimal places for currency amounts (default: 2)

### 3. Loan Configuration
Default loan parameters and limits.

- **LOAN_INTEREST_RATE**: Default annual interest rate for new loans (%)
- **MIN_LOAN_AMOUNT**: Minimum loan amount allowed
- **MAX_LOAN_AMOUNT**: Maximum loan amount allowed
- **MIN_LOAN_TERM**: Minimum loan term in months
- **MAX_LOAN_TERM**: Maximum loan term in months

### 4. Payments & Fees
Payment processing and fee configuration.

- **LATE_PAYMENT_FEE**: Late payment fee amount charged after grace period
- **LATE_PAYMENT_GRACE_DAYS**: Number of days grace period before charging late fee
- **PAYMENT_REMINDER_DAYS**: Days before due date to send payment reminder
- **EARLY_PAYMENT_DISCOUNT**: Discount percentage for early payments (%)

### 5. Notifications
Notification system configuration.

- **ENABLE_EMAIL_NOTIFICATIONS**: Enable email notifications for important events
- **ENABLE_SMS_NOTIFICATIONS**: Enable SMS notifications (requires SMS service configuration)
- **ADMIN_EMAIL**: Email address to receive admin notifications

### 6. System Settings
General system configuration.

- **MAINTENANCE_MODE**: Enable maintenance mode (only admins can access)
- **MAX_UPLOAD_SIZE_MB**: Maximum file upload size in megabytes
- **SESSION_TIMEOUT_MINUTES**: User session timeout in minutes

## Using Settings in Code

### Backend (Python/Django)

```python
from constance import config

# Access settings
company_name = config.COMPANY_NAME
interest_rate = config.LOAN_INTEREST_RATE
late_fee = config.LATE_PAYMENT_FEE

# Check boolean settings
if config.ENABLE_EMAIL_NOTIFICATIONS:
    send_email_notification(user)

if config.MAINTENANCE_MODE and not request.user.is_superuser:
    return render(request, 'maintenance.html')
```

### Frontend (Templates)

```django
{% load constance_tags %}

<!-- Access single config value -->
<h1>{% get_constance 'COMPANY_NAME' %}</h1>

<!-- Use in logic -->
{% get_constance 'MAINTENANCE_MODE' as maintenance %}
{% if maintenance %}
    <div class="alert">System is under maintenance</div>
{% endif %}
```

## Best Practices

### 1. Naming Conventions
- Use **UPPERCASE_WITH_UNDERSCORES** for setting names
- Be descriptive and clear
- Group related settings with common prefixes

### 2. Default Values
- Always provide sensible default values
- Defaults should allow the system to run without configuration

### 3. Validation
- Use appropriate data types (str, int, float, bool)
- Add clear help text for each setting
- Consider adding custom validation in forms if needed

### 4. Documentation
- Document each setting with clear description
- Explain the impact of changing the setting
- Provide examples of valid values

### 5. Security
- Never store sensitive data (passwords, API keys) in Constance
- Use environment variables for secrets
- Restrict access to superusers only

## Customization

### Adding New Settings

1. **Edit `backend/config/settings/base.py`:**

```python
CONSTANCE_CONFIG = {
    # ... existing settings ...

    'NEW_SETTING': (
        'default_value',
        'Description of what this setting does',
        type  # str, int, float, or bool
    ),
}
```

2. **Add to fieldset for organization:**

```python
CONSTANCE_CONFIG_FIELDSETS = {
    'Your Group Name': (
        'NEW_SETTING',
        # ... other settings in this group ...
    ),
}
```

3. **Restart the backend:**

```bash
docker-compose restart backend
```

### Custom Admin Styling

The Constance admin interface has been customized with Django Unfold styling in:
- `backend/apps/core/admin.py` - Custom admin class
- `backend/templates/unfold/admin/constance/change_form.html` - Custom template

## Troubleshooting

### Settings Not Showing
- Ensure Constance is in `INSTALLED_APPS`
- Run migrations: `python manage.py migrate constance`
- Check that you're logged in as superuser

### Changes Not Taking Effect
- Clear cache if using cache backend
- Restart Celery workers if settings affect background tasks
- Check that the setting name matches exactly (case-sensitive)

### Database Backend Issues
If using database backend (default), ensure:
```python
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
```

And run migrations:
```bash
python manage.py migrate constance
```

## Examples

### Loan Validation

```python
from constance import config
from django.core.exceptions import ValidationError

def validate_loan_amount(amount):
    if amount < config.MIN_LOAN_AMOUNT:
        raise ValidationError(
            f'Loan amount must be at least {config.MIN_LOAN_AMOUNT}'
        )
    if amount > config.MAX_LOAN_AMOUNT:
        raise ValidationError(
            f'Loan amount cannot exceed {config.MAX_LOAN_AMOUNT}'
        )
```

### Late Fee Calculation

```python
from constance import config
from datetime import timedelta

def calculate_late_fee(payment):
    grace_period = timedelta(days=config.LATE_PAYMENT_GRACE_DAYS)
    if payment.date > payment.due_date + grace_period:
        return config.LATE_PAYMENT_FEE
    return 0
```

### Currency Formatting

```python
from constance import config

def format_currency(amount):
    symbol = config.CURRENCY_SYMBOL
    places = config.DECIMAL_PLACES
    return f"{symbol}{amount:,.{places}f}"

# Usage
formatted = format_currency(1234.56)  # "$1,234.56"
```

## References

- [Django Constance Documentation](https://django-constance.readthedocs.io/)
- [Django Unfold Documentation](https://unfoldadmin.com/)
- [CrediFlux Settings Documentation](../config/settings/README.md)

## Support

For issues or questions about Constance configuration:
1. Check this documentation
2. Review Django Constance docs
3. Check application logs for errors
4. Contact the development team

---

**Last Updated:** 2025-10-29
**Version:** 1.0
