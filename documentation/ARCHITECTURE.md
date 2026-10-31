# Brightloop Subscription Management System — Architecture & Contracts

## 1. System Overview
Brightloop Subscription Management System is an Odoo 18 Community modular monolith with PostgreSQL 16 backing storage.

The system is developed collaboratively by four workstreams:
- `brightloop_core` (Member 1 - Foundation & Integration Lead)
- `brightloop_subscription` (Member 2 - Products & Subscriptions)
- `brightloop_billing` (Member 3 - Billing & Invoices)
- `brightloop_finance` (Member 4 - Payments & Finance)

---

## 2. Canonical Contracts

All workstreams must reference constants defined in `odoo.addons.brightloop_core.models.shared_constants`:

### User & Security Roles
- `admin`: Full administrative access
- `staff`: Operational management
- `customer`: Portal user with access strictly isolated to their own records

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

## 3. Workstream Rules
1. Never redefine shared statuses or create separate customer tables. Always extend `res.partner` or reference core contracts.
2. Cross-module dependencies must declare `brightloop_core` in their `__manifest__.py` `depends` list.
3. Keep security and data access backend-enforced via `ir.rule` and `ir.model.access.csv`.

