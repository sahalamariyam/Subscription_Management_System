# Brightloop Subscription Management System — Architecture & Contracts

## 1. System Overview
Brightloop Subscription Management System is an Odoo 18 Community modular monolith with PostgreSQL 16 backing storage.

The system is developed collaboratively by four workstreams:
- `brightloop_core` (Member 1 - Foundation, Authentication & Security Lead)
- `brightloop_subscription` (Member 2 - Products & Subscriptions)
- `brightloop_billing` (Member 3 - Billing & Invoices)
- `brightloop_finance` (Member 4 - Payments & Finance)

---

## 2. Canonical Contracts

All workstreams must reference constants defined in `odoo.addons.brightloop_core.models.shared_constants`:

### User & Security Roles
- `admin` (`brightloop_core.group_brightloop_admin`): Full administrative access, staff account management, and system configuration.
- `staff` (`brightloop_core.group_brightloop_staff`): Operational management (subscriptions, invoices, payments). Cannot manage security or create staff accounts.
- `customer` (`brightloop_core.group_brightloop_customer`): Portal user with access strictly isolated to their own records.

*(See `documentation/SECURITY.md` for complete security architecture, XML IDs, and ACL conventions.)*

### Subscription Lifecycle
- `draft`
- `quotation`
- `confirmed`
- `active`
- `closed`

### Invoice Lifecycle
- `draft`
- `confirmed`
- `paid`

### Billing Intervals
- `daily`
- `weekly`
- `monthly`
- `yearly`

---

## 3. Workstream Rules & Integration Boundaries
1. **Security Roles:** Never redefine shared statuses or create separate customer tables. Always extend `res.partner` or reference core contracts and security groups.
2. **Customer Isolation:** When defining subscription, billing, and payment models, always enforce record rules matching `[('partner_id', 'child_of', user.commercial_partner_id.id)]` for `group_brightloop_customer`.
3. **Cross-Module Dependencies:** Cross-module dependencies must declare `brightloop_core` in their `__manifest__.py` `depends` list.
4. **Backend Authorization:** Keep security and data access backend-enforced via `ir.rule` and `ir.model.access.csv`. Never rely on frontend view hiding.

---

## 4. Customer Portal & Integration Routes
Member 1 provides the portal foundation and integration placeholders for all other members:
- `/my` / `/my/home`: Customer portal dashboard.
- `/my/account`: Customer profile view and validated editing.
- `/my/security`: Customer password change with strict password policy enforcement.
- `/my/subscriptions` & `/my/quotations`: Portal integration endpoints for Member 2 (`brightloop_subscription`).
- `/my/invoices`: Portal integration endpoint for Member 3 (`brightloop_billing`).
- `/my/payments`: Portal integration endpoint for Member 4 (`brightloop_finance`).

*(See `documentation/PORTAL.md` and `documentation/AUTHENTICATION.md` for complete portal and auth workflow specifications.)*
