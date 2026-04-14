# Banking System Evaluation for CrediFlux

Repo under test: <https://github.com/saadmk11/banking-system>

## Quick take

This project is useful as a **UI/flow reference** for simple retail banking concepts, but it is **not a strong foundation** for CrediFlux's Finanzas/Banco module as-is.

## Pros

- Django-based, so easy to read and adapt
- Includes account types, deposits, withdrawals, transaction history
- Uses Celery for scheduled interest calculation
- Small and easy to spin up for demo review

## Cons

- Old stack: Django 3.2, Celery 4.4, SQLite by default
- Single-tenant and not built for enterprise accounting workflows
- More of a demo/concept app than a production-grade financial engine
- No serious bank reconciliation, journal entries, GL, multi-entity, permissions matrix, audit depth, or treasury workflows

## Better fit for CrediFlux

If the goal is **real finance/accounting engine**, `django-ledger` is the more serious candidate to evaluate next.

GitHub: <https://github.com/arrobalytics/django-ledger>

Why it looks stronger:
- Double-entry accounting core
- Better match for bank/finance module needs
- Closer to GL, journal, reporting, and financial statements
- More useful as embedded finance/accounting foundation than a banking demo UI

## Deployment notes

Demo compose for sweetmediabox is in `docker-compose.yml`.

Suggested demo URL/port:
- Web: `http://10.0.0.93:3640`
- Demo admin user: `demoadmin`
- Demo password: `demo2026`

## Recommendation

- **Install and review `saadmk11/banking-system` first** for quick inspiration/testing
- **Then evaluate `django-ledger`** if Juan wants something reusable for real implementation inside CrediFlux
