# Django Ledger Evaluation for CrediFlux

Repo under test: <https://github.com/arrobalytics/django-ledger>

## Why this is a better fit than saadmk11/banking-system

Django Ledger is much closer to what CrediFlux would need for a serious **Finanzas / Banco** module:

- Double-entry accounting
- Chart of accounts
- Journal entries and ledgers
- Financial statements
- Entity management
- Bank account information
- Multi-tenancy support
- Better accounting model than a retail-banking demo

## Demo deployment

Suggested test URL on sweetmediabox:
- `http://10.0.0.93:3640`

Suggested demo credentials:
- user: `demoadmin`
- pass: `demo2026`

## Caveats

- The repo ships mainly as a Django app / starter dev environment, not as a polished standalone product.
- Good candidate for architecture/reference and possibly embedding pieces into CrediFlux.
- We should evaluate:
  - bank reconciliation workflows
  - statement import
  - account hierarchy flexibility for RD financial entities
  - whether to embed engine concepts vs. adopt large chunks directly

## Recommendation

Use Django Ledger as the stronger benchmark/reference for CrediFlux finance/accounting architecture.
