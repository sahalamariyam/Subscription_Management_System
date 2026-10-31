# Brightloop Finance (`brightloop_finance`)

> **Workstream Owner:** Member 4 — Payments, Financial Dashboard & Reporting  
> **Odoo Version:** 18.0 Community  
> **Module Path:** `addons/brightloop_finance/`  
> **Branch:** `member-4`

---

## Overview

`brightloop_finance` is the payment and financial reporting module for the Brightloop Subscription Management System. It provides:

- **Payment recording** — manual entry with method, reference, and customer
- **Invoice allocation** — link one payment to multiple invoices (partial payments supported)
- **Outstanding & overdue tracking** — computed from native Odoo `account.move` fields
- **Financial dashboard** — 7 real-time KPI cards with date-range filtering
- **XLSX export** — 6 configurable report sheets downloadable as a single Excel file
- **Role-based access control** — enforced at ORM level (not just UI)

This module reads from other members' models but **never writes to them**. Billing calculations, subscription lifecycle, and invoice generation are entirely owned by other workstreams.

---

## Prerequisites & Dependencies

Install dependencies in this exact order — Odoo respects `depends[]` load order:

| # | Module | Owner | Purpose |
|---|---|---|---|
| 1 | `base`, `mail`, `account` | Odoo core | Base framework + `account.move` (invoice model) |
| 2 | `brightloop_core` | Member 1 | Canonical security groups, shared status constants, module category |
| 3 | `brightloop_billing` | Member 3 | Extends `account.move` with `subscription_id` field |

> **Important:** `brightloop_core` **must** load before `brightloop_billing`. The order in `__manifest__.py` is already correct — do not change it.

---

## Installation

### 1. Clone and checkout

```bash
git clone https://github.com/sahalamariyam/Subscription_Management_System.git
cd Subscription_Management_System
git checkout member-4       # finance module
git fetch origin feature/member-1-foundation member-3   # peer branches
```

### 2. Ensure `addons_path` includes this directory

In `config/odoo.conf`:
```ini
addons_path = /path/to/repo/addons,/usr/lib/python3/dist-packages/odoo/addons
```

### 3. Install Python dependency

```bash
pip install xlsxwriter
```

`xlsxwriter` is required for XLSX export. If it is missing, all other features work normally — only the export button raises a user-friendly error.

### 4. Install the module

```bash
# Via Odoo CLI
./odoo-bin -d brightloop_dev -i brightloop_finance --stop-after-init

# Or via Docker (if docker-compose.yml is present from Member 1's branch)
docker-compose up -d
docker exec -it <odoo_container> ./odoo-bin -d brightloop_dev -i brightloop_finance --stop-after-init
```

### 5. Upgrade after code changes

```bash
./odoo-bin -d brightloop_dev -u brightloop_finance --stop-after-init
```

---

## User Roles

Roles are defined under the **Brightloop** category in **Settings → Users & Companies → Groups**.

| Role | XML ID | Inherits | Permissions |
|---|---|---|---|
| **Finance User** | `brightloop_finance.group_brightloop_finance_user` | `brightloop_core.group_brightloop_staff` | Record payments, view invoices & dashboard, run exports |
| **Finance Manager** | `brightloop_finance.group_brightloop_finance_manager` | Finance User + `brightloop_core.group_brightloop_admin` | All above + configure payment methods, delete records, access all customers |

### Assigning roles

1. Go to **Settings → Users & Companies → Users**
2. Open a user record
3. Under the **Brightloop** section, select **Finance User** or **Finance Manager**

### Customer (Portal) access

Customers assigned `brightloop_core.group_brightloop_customer` can:
- View **their own** payments and allocations (read-only)
- Cannot access any other customer's financial data

This isolation is enforced at the **ORM record-rule level** — it cannot be bypassed by direct API calls.

---

## Configuration

### Payment Methods

Six payment methods are seeded automatically on install (`data/payment_method_data.xml`, `noupdate="1"`):

| Method | Code | Requires Reference |
|---|---|---|
| Cash | `cash` | No |
| Bank Transfer | `bank_transfer` | Yes — UTR / bank ref |
| Credit / Debit Card | `card` | No |
| Cheque | `cheque` | Yes — cheque number |
| Online Gateway | `gateway` | Yes — transaction ID |
| UPI | `upi` | No |

To add or edit methods: **Finance → Configuration → Payment Methods**  
(Finance Manager role required)

> Seeded methods use `noupdate="1"` — renaming them in the UI will not be overwritten on module upgrade.

---

## Key Models

### `brightloop.payment`

Central payment record. Each payment represents a single receipt of funds from a customer.

| Field | Type | Description |
|---|---|---|
| `name` | `Char` | Auto-sequence `PAY/YYYY/NNNNN` |
| `partner_id` | `Many2one → res.partner` | Customer |
| `payment_method_id` | `Many2one → brightloop.payment.method` | How funds were received |
| `amount` | `Monetary` | Total amount received |
| `payment_date` | `Date` | Date of receipt |
| `reference` | `Char` | Bank ref / transaction ID |
| `state` | `Selection` | `draft` → `posted` → `cancelled` |
| `total_allocated` | `Monetary` (computed) | Sum across all allocation lines |
| `unallocated_amount` | `Monetary` (computed) | `amount - total_allocated` |
| `is_fully_allocated` | `Boolean` (computed) | True when `unallocated_amount = 0` |
| `is_overpayment` | `Boolean` (computed) | True when `total_allocated > amount` |

**State transitions:**

```
draft ──[Confirm]──► posted ──[Cancel]──► cancelled
  ▲                                           │
  └──────────────[Reset to Draft]─────────────┘
```

Only `posted` payments are counted in revenue KPIs and export reports.

---

### `brightloop.invoice.payment`

Allocation join table — links one payment to one invoice with a specific allocated amount.

| Field | Type | Description |
|---|---|---|
| `payment_id` | `Many2one → brightloop.payment` | The payment record |
| `invoice_id` | `Many2one → account.move` | The invoice (Odoo native) |
| `partner_id` | `Many2one → res.partner` | Denormalised for fast portal queries |
| `allocated_amount` | `Monetary` | Amount applied to this invoice |
| `allocation_date` | `Date` | Date of allocation |

> **Important:** This model is a *tracking layer only*. It does **not** write to `account.move`. Odoo manages `amount_residual` and `payment_state` through its own reconciliation engine. The two systems are intentionally kept independent.

---

### `brightloop.finance.dashboard` (Transient)

Used as a data-aggregation controller for the dashboard. Not persisted.

All KPIs use `read_group()` for database-level aggregation — no Python-level loops over full record sets.

---

### `brightloop.finance.export` (Transient Wizard)

Generates XLSX reports. Inherits `brightloop.finance.report` for authorization.

---

## Financial Dashboard

Navigate to **Finance → Dashboard**.

| KPI Card | Source | Notes |
|---|---|---|
| Active Subscriptions | `brightloop.subscription` | `status=active AND is_paused=False` |
| Paused Subscriptions | `brightloop.subscription` | `status=active AND is_paused=True` |
| Revenue Received | `brightloop.invoice.payment` | Posted payments in date range |
| Total Outstanding | `account.move` | Sum of `amount_residual` on posted invoices |
| Overdue Invoices (count) | `account.move` | Past `invoice_date_due`, unpaid, posted |
| Overdue Amount | `account.move` | Sum of `amount_residual` on overdue invoices |
| Total Invoiced | `account.move` | Sum of `amount_total` on posted invoices |

**Date filter** defaults to the current calendar month. Change **From / To** and click **Refresh**.

---

## XLSX Export

Navigate to **Finance → Reports → Export Financial Report**.

### Available Report Types

| Type | Sheets Generated |
|---|---|
| Payment History | Payment History |
| All Invoices | All Invoices |
| Outstanding Invoices | Outstanding |
| Overdue Invoices | Overdue |
| Revenue Summary | Revenue Summary |
| Subscription Information | Subscriptions |
| **Full Financial Report** (default) | **All 6 sheets** |

### Revenue Summary Sheet columns

| Col | Name | Source |
|---|---|---|
| A | Month | Merged from all three data sources |
| B | Revenue Received | `sum(allocated_amount)` grouped by `allocation_date:month` |
| C | Total Invoiced | `sum(amount_total)` on `account.move` grouped by `invoice_date:month` |
| D | Outstanding Balance | `sum(amount_residual)` on `account.move` where `amount_residual > 0` |

### Filters

- **Date From / To** — mandatory, defaults to current year
- **Customer** — optional; Finance Managers can export all customers; portal users are restricted to their own
- **Subscription** — optional; filters invoice and payment sheets to one subscription

---

## Integration Points

### With Member 1 (`brightloop_core`)

```python
# Security groups used in record rules and access checks
'brightloop_core.group_brightloop_customer'  # portal isolation rules
'brightloop_core.group_brightloop_staff'     # implied by Finance User
'brightloop_core.group_brightloop_admin'     # implied by Finance Manager

# Shared constants imported in models and report
from odoo.addons.brightloop_core.models.shared_constants import (
    SUBSCRIPTION_STATUS_ACTIVE,    # 'active'
    SUBSCRIPTION_STATUS_CLOSED,    # 'closed'
    # ... etc.
)
```

> Both `brightloop_finance_report.py` and `finance_export.py` include a `try/except ImportError` fallback with inline literals that exactly match `shared_constants.py` values — the module installs even if `brightloop_core` is temporarily absent during development.

---

### With Member 2 (`brightloop.subscription`)

Fields accessed (read-only):

| Field | Type | Used in |
|---|---|---|
| `status` | `Selection` | Dashboard KPI counts, export filter |
| `is_paused` | `Boolean` | Active vs. Paused KPI split |
| `partner_id` | `Many2one` | Customer identity |
| `subscription_number` | `Char` | Export sheet display |
| `plan_id` | `Many2one` | Export sheet display |
| `start_date` / `expiry_date` | `Date` | Export sheet display |
| `next_billing_date` | `Date` | Export sheet display |

We **never write** to `brightloop.subscription`.

---

### With Member 3 (`brightloop_billing` / `account.move`)

Invoice model: **`account.move`** (Odoo 18 native, `move_type = 'out_invoice'`)

| `account.move` field | Logical name | Used in |
|---|---|---|
| `amount_total` | Total invoice value | Dashboard, export |
| `amount_residual` | Outstanding balance | Dashboard overdue, export |
| `invoice_date_due` | Due date | Overdue detection |
| `invoice_date` | Invoice date | Date range filter |
| `name` | Invoice number | Export display |
| `state` | Draft / Posted / Cancelled | Base domain filter |
| `payment_state` | Payment status | Overdue filter, export label |
| `partner_id` | Customer | Isolation filter |
| `subscription_id` | Linked subscription | Export filter, display (added by Member 3 via `_inherit`) |

We **never write** to `account.move`.

---

## Running Tests

```bash
# Run all brightloop_finance tests
./odoo-bin -d brightloop_dev \
  --test-enable \
  --test-tags brightloop_finance \
  --stop-after-init

# Run a specific test file
./odoo-bin -d brightloop_dev \
  --test-enable \
  --test-tags /brightloop_finance/tests/test_payment \
  --stop-after-init
```

### Test Coverage (31 tests)

| File | Tests | Covers |
|---|---|---|
| `tests/test_payment.py` | 11 | Payment creation, state machine, sequence, duplicate prevention, compute fields |
| `tests/test_allocation.py` | 14 | Single/partial/multiple allocation, overpayment, over-allocation guard, `amount_residual` reading |
| `tests/test_dashboard.py` | 6 | All 7 KPI values, date filter, overdue detection |

---

## Performance Notes

All dashboard queries and export aggregations use `read_group()` (SQL `GROUP BY`) — no Python-level loops over unbounded record sets.

Database indexes created in `models.init()`:

| Index | Table | Columns | Purpose |
|---|---|---|---|
| `idx_bl_pay_date_state` | `brightloop_payment` | `payment_date, state` | Dashboard date-range + state filter |
| `idx_bl_pay_partner_date` | `brightloop_payment` | `partner_id, payment_date` | Portal user queries |
| `idx_bl_invpay_invoice` | `brightloop_invoice_payment` | `invoice_id` | Allocation lookup by invoice |
| `idx_bl_invpay_partner` | `brightloop_invoice_payment` | `partner_id` | Portal isolation |
| `idx_bl_invpay_date` | `brightloop_invoice_payment` | `allocation_date` | Revenue summary grouping |
| `idx_bl_invpay_pay_date` | `brightloop_invoice_payment` | `payment_id, allocation_date` | Payment + date compound filter |

---

## Project Structure

```
addons/brightloop_finance/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── brightloop_payment.py           # BrightloopPaymentMethod + BrightloopPayment
│   ├── brightloop_invoice_payment.py   # BrightloopInvoicePayment (allocation)
│   └── brightloop_finance_report.py    # Dashboard transient + report abstract model
├── wizard/
│   ├── payment_wizard.py               # PaymentWizard (guided payment + allocation entry)
│   └── payment_wizard_views.xml
├── report/
│   ├── finance_export.py               # BrightloopFinanceExport (6-sheet XLSX)
│   └── finance_export_views.xml
├── views/
│   ├── payment_views.xml
│   ├── invoice_payment_views.xml
│   └── dashboard_views.xml
├── security/
│   ├── security_groups.xml             # Finance User + Finance Manager groups
│   ├── record_rules.xml                # ORM-level customer isolation
│   └── ir.model.access.csv
├── data/
│   ├── sequence_data.xml               # PAY/YYYY/NNNNN
│   └── payment_method_data.xml         # 6 default methods
└── tests/
    ├── test_payment.py                 # 11 tests
    ├── test_allocation.py              # 14 tests
    └── test_dashboard.py              # 6 tests
```

---

## Hackathon Submission Checklist

| Requirement | Status |
|---|---|
| Payments recorded with method, date, reference, customer | ✅ |
| Payments allocated to invoices | ✅ |
| Partial payments supported | ✅ |
| Outstanding balances correct (from `amount_residual`) | ✅ |
| Overdue invoices identified and counted | ✅ |
| Dashboard KPI metrics accurate | ✅ |
| Date-range and customer filters | ✅ |
| Excel export with all 6 sheets | ✅ |
| Authorization enforced at ORM level | ✅ |
| Database indexes added | ✅ |
| Tests written (31 total) | ✅ |
| Integration with all 3 members' contracts | ✅ |
| Module in `addons/` (matches team structure) | ✅ |
| Documentation | ✅ |
