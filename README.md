# Events360 — Backend

Central multi-tenant admin/control plane for the FashioNXT suite (EventNXT, CastNXT, PlaNXT).

**Status: Foundation slice.** This covers org signup, platform admin login,
and the org approval flow end-to-end. RBAC, lifecycle/deletion policies,
post-event retention, and the OAuth2 provider role are built in later slices.

## Stack
FastAPI + SQLAlchemy + Alembic + Postgres, deployed on Heroku.

## What's implemented so far

- POST /organizations/signup — creates an Organization (pending_approval) + its owner User
- POST /auth/login — org user login (blocked until the org is approved)
- POST /admin/login — platform admin login
- GET /admin/organizations/pending — list orgs awaiting approval (admin-only)
- POST /admin/organizations/{id}/approve — approves an org, logs the decision
- POST /admin/organizations/{id}/deny — denies an org, logs the decision
- Password policy enforced server-side on signup: 8+ characters, 1 number, 1 special character

## Not yet built (next slices)

1. RBAC — Permission / Role / RolePermission / StaffAssignment
2. Platform admin self-service — superadmin creating support_admin accounts via API
3. Lifecycle — 30-day inactivity auto-deactivation job, org/event deletion, locked status
4. Post-event data retention job + 14-day reminder email
5. OAuth2 provider (Authlib) — held until EventNXT is being built