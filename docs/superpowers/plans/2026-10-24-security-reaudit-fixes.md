# Security re-audit (run-2) fix wave — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the confirmed findings of the run-2 re-audit (1 high, 5 medium, 5 low) so a scoped re-verification (run-3) can grade the branch A.

**Architecture:** One task per finding. The spec record (a JSON file under `~/security-audit-skill/CrediFlux/run-2/final-records/`) is the authority: it holds the trace, the invariant (`intended_behavior`), the remediation strategy with suggested code, and the regression case to add. Each task applies the fix at the decision point the record names, reusing the existing controls (`apps/users/lockout.py`, `apps/core/permissions.TenantMatches`, `apps/loans/policy.py`) rather than duplicating them, and adds the regression test the record's `remediation.strategy` describes.

**Tech Stack:** Django 5 / DRF, django-tenants; pytest with the project fixtures (`backend/conftest.py`: `tenant_schema`, `user_factory`, `auth_client`, `api_client`; factories in `backend/tests/factories.py`).

**Spec:** `~/security-audit-skill/CrediFlux/run-2/findings.json` (same records, validated) and `~/security-audit-skill/CrediFlux/run-2/REPORT.md` §5–§6.

**Status (2026-10-24):** executed in full (11 tasks, commits `d24ee01..6f126ce`, suite 677 passed after the merge of master in `3af68a4`). Ledger with rulings and deferred minors: `.superpowers/sdd/2026-10-24-security-reaudit-fixes/progress.md`. Re-verified by run-3 (`~/security-audit-skill/CrediFlux/run-3/REPORT.md`).

## Global Constraints

- Work only in the worktree `/Users/JuanPerez/Documents/Django Projects/CrediFlux-v2/.claude/worktrees/security-remediation` (branch `claude/security-remediation`). Never `cd` to the parent checkout.
- Tests run only with `bash .superpowers/sdd/2026-10-23-security-audit-remediation/pytest-docker.sh <pytest args>`; `manage.py` only through `manage-docker.sh` in the same directory. Use `--create-db` after adding a migration.
- New user-facing messages in Spanish. No new dependencies.
- The existing suite stays green (562 passed at fadbad7). New tests go in `backend/apps/<app>/tests/test_security_<topic>.py`.
- Never weaken a control to make a test pass. Do not touch `frontend/`.
- One commit per task.

## Review Focus

1. Task 1: the admin login must give no authenticated session to a user with `is_2fa_enabled` until a valid TOTP or backup code is presented; non-2FA users are unaffected.
2. Task 1: removing DRF `SessionAuthentication` must not break the Django admin (plain Django sessions) nor the existing tests that log in with a session and then call `/api/` routes: keep session use for `/admin/`, switch to JWT for `/api/`.
3. Task 6: the re-authentication counter is keyed by user id (not email+IP) so a token holder cannot lock the victim out of the login door; once exhausted, even the correct password is refused until the window expires.
4. Task 5: loan term fields remain editable while the loan is `pending` and no non-archived contract carries a signature.
5. Task 3: `CashSession.register` moving to `PROTECT` needs a migration; register destroy answers 400, not 500, when sessions exist.

---

Every task follows the same steps: (1) read the spec record; (2) write the regression test(s) the record's `remediation.strategy` describes, run them, confirm they fail; (3) implement the record's remediation at the named files; (4) focused tests pass, then the full suite; (5) commit.

### Task 1: Second factor on the Django admin door; DRF stops accepting Django sessions
- Spec record: `users.admin-login.password-only-session.session-auth-api-2fa-step-up-bypass` (**high**).
- Files: `backend/apps/users/admin_forms.py` (new form installed as `admin.site.login_form` from `backend/apps/users/lockout.py`), `backend/templates/admin/login.html`, `backend/config/settings/base.py` (`DEFAULT_AUTHENTICATION_CLASSES` without `SessionAuthentication`), `backend/apps/tenants/middleware.py`.
- Tests: `backend/apps/users/tests/test_security_admin_2fa.py`.

### Task 2: Role permission on the task board
- Spec record: `communications/TaskViewSet:missing-role-permission-on-task-writes` (**medium**).
- Files: `backend/apps/communications/permissions.py` (`CanManageTasks`), `backend/apps/communications/views.py`, `backend/apps/communications/serializers.py`.
- Tests: `backend/apps/communications/tests/test_security_tasks.py`.

### Task 3: Closed cash sessions are immutable on every path
- Spec record: `crediflux.cashbox.closed-session-immutability-only-on-movement-viewset` (**medium**).
- Files: `backend/apps/cashbox/models.py` (`PROTECT`) + migration `0002`, `backend/apps/cashbox/views.py`.
- Tests: `backend/apps/cashbox/tests/test_security_cashbox_closed.py`.

### Task 4: Rate cap honours interest type and payment frequency
- Spec record: `crediflux.loans.policy.rate-cap-ignores-variable-rd-per-period-rate` (**medium**).
- Files: `backend/apps/loans/policy.py` (`annual_nominal_rate`), `backend/apps/loans/serializers.py`.
- Tests: `backend/apps/loans/tests/test_security_rate_cap.py`.

### Task 5: Approved or signed loans keep their borrower and terms
- Spec record: `loans.LoanSerializer.post-approval-terms-and-customer-writable` (**medium**).
- Files: `backend/apps/loans/serializers.py` (`_ensure_terms_editable`), `backend/apps/loans/views.py` (`disburse` re-runs `validate_approval`; a pending-loan term edit recomputes the installment and regenerates the unsigned contract).
- Tests: `backend/apps/loans/tests/test_security_loan_terms_lock.py`.

### Task 6: Attempt budget for current-password re-checks
- Spec record: `users.current-password-checks.no-attempt-budget.change-password-2fa-disable-backup-codes-oracle` (**medium**).
- Files: `backend/apps/users/lockout.py` (`check_reauth_password`), `backend/apps/users/serializers.py`.
- Tests: `backend/apps/users/tests/test_security_reauth.py`.

### Task 7: e-CF provider paths honour the invoice state machine
- Spec record: `crediflux.billing.ecf-provider-submit-cancel-bypass-invoice-state-machine` (**low**).
- Files: `backend/apps/billing/services/ecf_provider.py` (shared guards; DirectDGII requires `signed`), `backend/apps/billing/services/nexconnect/provider.py`, `backend/apps/billing/views.py`.
- Tests: `backend/apps/billing/tests/test_security_ecf_provider_state.py`.

### Task 8: Seat limit enforced in the Django admin too
- Spec record: `crediflux/apps.users.admin/UserAdmin/max-users-seat-cap-bypass` (**low**).
- Files: `backend/apps/users/quota.py`, `backend/apps/users/admin.py`.
- Tests: `backend/apps/users/tests/test_security_admin_seats.py`.

### Task 9: Only pending or rejected loans can be deleted
- Spec record: `loans.LoanViewSet.destroy-no-status-guard` (**low**).
- Files: `backend/apps/loans/views.py` (`perform_destroy`).
- Tests: `backend/apps/loans/tests/test_security_loan_destroy.py`.

### Task 10: Registration cap charged per provisioning attempt
- Spec record: `tenants.registration.daily-cap-uncharged-on-post-provisioning-rollback` (**low**).
- Files: `backend/apps/tenants/serializers.py` (cache-backed daily budget charged before provisioning; owner username made unique).
- Tests: `backend/apps/tenants/tests/test_security_registration_cap.py`.

### Task 11: Per-client daily registration budget
- Spec record: `tenants.registration.global-daily-cap-fillable-by-single-requester` (**low**).
- Files: `backend/apps/tenants/serializers.py`, `backend/config/settings/base.py` (`MAX_TENANTS_PER_IP_PER_DAY`).
- Tests: `backend/apps/tenants/tests/test_security_registration_cap.py`.
- Note: recorded as a mitigation, not a full closure (provisioning after e-mail verification remains follow-up #38); run-3 re-raised it as a low.
