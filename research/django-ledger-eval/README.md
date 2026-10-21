# Django Ledger Evaluation for CrediFlux

Repo under test now uses the official starter:
- <https://github.com/arrobalytics/django-ledger-starter>

This is a better demo target than the main development repo because it is lighter and intended as a zero-config starting point.

## Demo URL
- `http://10.0.0.93:3640`

## Demo credentials
- user: `demoadmin`
- pass: `demo2026`

## Why this matters for CrediFlux

Django Ledger is still the stronger benchmark for a future **Finanzas / Banco** module because it brings:
- double-entry accounting
- chart of accounts
- journals / ledgers
- financial statements
- bank account structures
- better accounting architecture than a basic banking demo

## Recommendation

Use this deployment for product review, but for CrediFlux I would use it mainly as:
1. architecture reference,
2. accounting engine inspiration,
3. possible source of patterns/components to embed,
not as a drop-in replacement for the whole finance module.
