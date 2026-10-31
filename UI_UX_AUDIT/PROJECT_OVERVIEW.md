# PROJECT OVERVIEW: BRIGHTLOOP SUBSCRIPTION MANAGEMENT SYSTEM

> **Document Type:** Senior Architectural & UI/UX Audit — Document 01 / 08  
> **Auditor Role:** Senior UI/UX Auditor, Software Architect & Frontend Reverse Engineer  
> **Project Name:** Brightloop Subscription Management System  
> **Target Downstream Consumer:** Google Stitch AI (Frontend Reconstruction & Modernization)  
> **Repository Path:** `/Users/noelsabu/Documents/subcription_management_oduu /`  
> **Audit Date:** October 31, 2026  
> **Scope:** Entire application frontend, backend UI, web controllers, OWL components, and data interfaces.

---

## 1. Project Purpose & Business Context

**Brightloop Subscription Management System** is an enterprise-grade SaaS subscription lifecycle, billing automation, and financial management platform. Built natively for **Odoo 18.0 Community**, it bridges the gap between commercial product/plan configuration, complex recurring subscription lifecycles, automated multi-company customer invoice generation, partial payment allocations, financial analytics, and customer self-service access.

The system was developed collaboratively by four dedicated engineering workstreams:
1. **Member 1 (Platform Foundation, Authentication & Security Lead):** `brightloop_core` — Platform identity, canonical roles, strict password policies, tenant data isolation, customer portal home, and HTTP web controller infrastructure.
2. **Member 2 (Product, Plan, Quotation & Subscription Lifecycle Lead):** `brightloop_subscription` — Product catalog, variant adjustments, subscription plan governance, quotation templates, and full commercial lifecycle state machine (`draft` -> `quotation` -> `confirmed` -> `active` -> `closed`).
3. **Member 3 (Billing, Invoice Management, Tax & Discount Lead):** `brightloop_billing` — Automated recurring billing engine, `account.move` customer invoice generation, billing job tracking (`brightloop.billing.job`), row-level concurrency locking (`FOR UPDATE NOWAIT`), discount aggregation, company tax assignment, and daily scheduled execution (`ir.cron`).
4. **Member 4 (Payment Management & Financial Reporting Lead):** `brightloop_finance` — Manual and gateway payment recording (`brightloop.payment`), invoice-to-payment allocation join model (`brightloop.invoice.payment`), payment recording wizard (`brightloop.payment.wizard`), 6-sheet XLSX financial export (`brightloop.finance.export`), and real-time OWL 2 Financial Dashboard (`brightloop_finance_dashboard`).

---

## 2. Complete Technology Stack

| Layer | Technology | Specification / Details |
|---|---|---|
| **Base Platform & Runtime** | Odoo 18.0 Community | Python 3.12, modular monolith architecture |
| **Database & Backing Store** | PostgreSQL 16 | Relational storage, ACID transactions, `FOR UPDATE NOWAIT` row locking, schema constraints, custom performance indexes |
| **Backend Framework** | Odoo ORM (`odoo.models`) | `models.Model` (persistent tables), `models.TransientModel` (wizards/controllers), `models.AbstractModel` (reporting utilities) |
| **Frontend Frameworks** | OWL 2 & QWeb | **OWL 2** (Odoo Web Library) for interactive single-page client actions; **Server-side QWeb** for customer portal templates and administrative form/list/search views |
| **Authentication & Sessions** | Native Odoo Session Store + Passlib | Cookie-based session tracking (`session_id`), PBKDF2-SHA512 password hashing (600,000 rounds), custom HMAC cryptographic tokens for password reset |
| **Authorization & RBAC** | Odoo Security Subsystem | Security categories (`ir.module.category`), groups (`res.groups`), model-level ACLs (`ir.model.access.csv`), and row-level record rules (`ir.rule`) |
| **Routing & Controllers** | Odoo HTTP Routing Engine | `@http.route()` decorator, Werkzeug WSGI server, JSON-RPC (`/web/dataset/call_kw`) for OWL component APIs |
| **UI Component System** | Odoo Web Client + Bootstrap 5 | Odoo 18 web views (`list`, `form`, `search`, `client action`), Bootstrap 5 CSS classes, FontAwesome 4.7 / 5 icon sets |
| **State Management** | OWL `useState` + Reactive State | Client-side reactive proxies (`useState`) inside OWL components; server-side database state persisted in PostgreSQL |
| **Styling & Preprocessing** | SCSS / CSS3 | Scoped SCSS stylesheets (`dashboard.scss`), CSS Custom Properties (`var(--body-font-family)`), Bootstrap utility classes |
| **Reporting & File Export** | `xlsxwriter` + Base64 Streaming | In-memory spreadsheet generation (`io.BytesIO`), formatted multi-sheet binary download |
| **Deployment & Orchestration**| Docker & Docker Compose | Multi-container setup (`web` container on Python 3.12 + `db` container on PostgreSQL 16) |

---

## 3. High-Level Application Architecture

The system is organized as a modular monolith adhering to a strict vertical dependency graph:

```
                      ┌───────────────────────────┐
                      │      brightloop_core      │  (Platform, Security, Portal, Auth)
                      └─────────────┬─────────────┘
                                    │
                      ┌─────────────▼─────────────┐
                      │  brightloop_subscription  │  (Catalog, Plans, Quotes, Lifecycles)
                      └─────────────┬─────────────┘
                                    │
                      ┌─────────────▼─────────────┐
                      │    brightloop_billing     │  (Recurring Engine, Invoices, Jobs)
                      └─────────────┬─────────────┘
                                    │
                      ┌─────────────▼─────────────┐
                      │    brightloop_finance     │  (Payments, Allocations, OWL Dashboard)
                      └───────────────────────────┘
```

### Module Breakdown & Architectural Scope

### 1. `brightloop_core` (Platform & Identity)
- **Directory:** `addons/brightloop_core/`
- **Manifest Dependencies:** `base`, `mail`, `portal`, `auth_signup`
- **Models:**
  - `res.users` (Inherited): Canonical role computation (`brightloop_role`), strict password policy validation (`_validate_password_policy`), privilege escalation guard (`_check_escalation_attempt`).
  - `res.partner` (Inherited): Portal user linking, commercial customer isolation mapping.
  - `shared_constants.py`: Single canonical source of truth for all platform constants (roles, subscription states, invoice states, billing intervals).
- **Controllers:**
  - `BrightloopAuthSignupHome` (`controllers/main.py`): Anti-enumeration password reset endpoint (`/web/reset_password`), email syntax verification.
  - `BrightloopCustomerPortal` (`controllers/portal.py`): Customer portal home counters (`_prepare_home_portal_values`), profile validation (`details_form_validate`), paginated routes for `/my/subscriptions`, `/my/quotations`, `/my/invoices`, `/my/payments`.
- **Views & UI:**
  - `portal_templates.xml`: QWeb templates for customer portal home dashboard, subscription list/detail, quotation list, invoice list/detail, payment history.
  - `staff_views.xml`: Admin-only Staff Management interface (`res.users` list and form views).

### 2. `brightloop_subscription` (Commercial Subscription Engine)
- **Directory:** `addons/brightloop_subscription/`
- **Manifest Dependencies:** `base`, `mail`, `portal`, `account`, `brightloop_core`
- **Models:**
  - `brightloop.product`: Products with type (`software`, `addon`, `service`), sales price, cost price, and notes.
  - `brightloop.product.variant`: Variants with price adjustments (`price_adjustment`) and calculated `effective_price`.
  - `brightloop.plan`: Subscription plans with cadence (`daily`, `weekly`, `monthly`, `yearly`), billing interval count, minimum quantity, anchor day preservation, and governance permissions (`auto_close`, `allow_early_close`, `allow_pause`, `allow_renewal`).
  - `brightloop.quotation.template`: Pre-configured quotation templates with default validity and line presets.
  - `brightloop.subscription`: Central commercial entity tracking canonical status (`draft` -> `quotation` -> `confirmed` -> `active` -> `closed`), pause/resume mechanics, renewal counter, and early closure verification.
  - `brightloop.subscription.line`: Line items linking products, variants, quantities, unit prices, discounts, and taxes.
- **Views & UI:**
  - `menu_views.xml`: Top-level "Brightloop Subscriptions" application menu with submenus for Subscriptions, Catalog & Plans, and Configuration.
  - `subscription_views.xml`: List, form, and search views for subscriptions; action buttons for lifecycle transitions.
  - `plan_views.xml`: List, form, and search views for subscription plans.
  - `product_views.xml`: List, form, and search views for products and variants.
  - `quotation_template_views.xml`: List and form views for sales quotation templates.

### 3. `brightloop_billing` (Recurring Invoicing & Jobs)
- **Directory:** `addons/brightloop_billing/`
- **Manifest Dependencies:** `base`, `account`, `mail`, `brightloop_core`, `brightloop_subscription`
- **Models:**
  - `account.move` (Inherited): Extended with `subscription_id` (`Many2one -> brightloop.subscription`, indexed, copy=False, ondelete='restrict').
  - `brightloop.billing.job`: Audit log for every recurring billing execution with deterministic `idempotency_key`, period start/end, attempt timestamps, execution status (`pending`, `done`, `failed`), and error tracking.
  - `brightloop.billing.engine` (Transient): Automated processing engine executed via daily cron (`ir.cron`). Handles row locking (`55P03` lock handling), multi-company context isolation, transaction savepoints, combined discount resolution, and draft customer invoice generation.
- **Views & UI:**
  - `brightloop_billing_job_views.xml`: List, form, and search views for audit inspection of billing jobs.

### 4. `brightloop_finance` (Payments & Financial Dashboard)
- **Directory:** `addons/brightloop_finance/`
- **Manifest Dependencies:** `base`, `mail`, `account`, `brightloop_core`, `brightloop_subscription`, `brightloop_billing`
- **Models:**
  - `brightloop.payment.method`: Configurable payment methods (`cash`, `bank_transfer`, `card`, `cheque`, `gateway`, `upi`).
  - `brightloop.payment`: Customer payment records with sequential numbering (`PAY/YYYY/NNNNN`), state machine (`draft` -> `posted` -> `cancelled`), duplicate reference constraints, and allocation compute fields (`total_allocated`, `unallocated_amount`, `is_fully_allocated`, `is_overpayment`).
  - `brightloop.invoice.payment`: Join model mapping payments to native `account.move` customer invoices with balance validation.
  - `brightloop.payment.wizard` (Transient): Interactive modal wizard for recording a payment and allocating it against customer invoices in a single transaction.
  - `brightloop.finance.export` (Transient): 6-sheet XLSX financial reporting wizard.
  - `brightloop.finance.dashboard` (Transient): In-memory KPI aggregator and JSON-RPC API endpoint (`get_dashboard_kpis()`).
- **Views & UI:**
  - `dashboard_views.xml`: Client action registration for OWL Dashboard (`action_finance_dashboard_owl`) and fallback form view.
  - `payment_views.xml`: List, form, search views for payments and payment methods.
  - `invoice_payment_views.xml`: List, form, search views for payment allocations.
  - `payment_wizard_views.xml`: Modal popup form for recording payments.
  - `finance_export_views.xml`: Modal popup form for generating and downloading XLSX financial reports.
  - `static/src/`: OWL 2 Frontend Dashboard component (`dashboard.js`, `dashboard.xml`, `dashboard.scss`).

---

## 4. User Roles & Permission Matrix

The application enforces a 3-tier canonical role hierarchy under `brightloop_core.module_category_brightloop`:

```
┌─────────────────────────────────────────────────────────────┐
│                 Brightloop Administrator                    │
│          (brightloop_core.group_brightloop_admin)           │
│   Full administrative authority, staff account creation,     │
│   system configuration, billing job audit, all domains      │
└──────────────────────────────┬──────────────────────────────┘
                               │ (implies)
┌──────────────────────────────▼──────────────────────────────┐
│                      Brightloop Staff                       │
│          (brightloop_core.group_brightloop_staff)           │
│   Operational management: subscriptions, catalog, invoices, │
│   payments, dashboard; strictly prohibited from security    │
│   management or staff account creation                      │
└──────────────────────────────┬──────────────────────────────┘
                               │ (inherits base.group_user)
┌──────────────────────────────▼──────────────────────────────┐
│                    Brightloop Customer                      │
│        (brightloop_core.group_brightloop_customer)          │
│   External self-service portal: strictly isolated to own    │
│   profile, subscriptions, invoices, and payments            │
└─────────────────────────────────────────────────────────────┘
```

### Specialized Functional Role Overlays (Finance Workstream)

| Functional Role | Odoo XML ID | Inherits / Implies | Capabilities |
|---|---|---|---|
| **Finance User** | `brightloop_finance.group_brightloop_finance_user` | `brightloop_core.group_brightloop_staff` | Record payments, view dashboard, allocate invoices, run exports |
| **Finance Manager**| `brightloop_finance.group_brightloop_finance_manager` | `group_brightloop_finance_user` + `brightloop_core.group_brightloop_admin` | Configure payment methods, delete records, access all customers |

### Data Isolation & Access Control Summary

| Security Boundary | Technical Mechanism | Enforcement Level |
|---|---|---|
| **Customer Data Isolation** | PostgreSQL record rules (`ir.rule`) using `[('partner_id', 'child_of', user.commercial_partner_id.id)]` | Database Query Level |
| **Staff Privilege Escalation** | ORM hook overrides on `res.users.create()` and `res.users.write()` preventing non-admins from modifying `groups_id` or creating internal accounts | Python / ORM Level |
| **Password Policy** | Regex validation (`_validate_password_policy`): minimum 12 chars, uppercase, lowercase, special character | Controller + Model Level |
| **Report Authorization** | Python helper `_check_report_access(partner_id)` preventing non-admins/non-staff from viewing other partner records | Abstract Model Level |

---

## 5. Architectural Contracts Between Modules

| Contract | Origin Module | Consumer Module | Technical Implementation |
|---|---|---|---|
| **Shared Constants** | `brightloop_core` | All modules | `from odoo.addons.brightloop_core.models.shared_constants import ...` |
| **Subscription Reference** | `brightloop_subscription` | `brightloop_billing` | `sub = env['brightloop.subscription']._get_subscriptions_due_for_billing()` |
| **Invoice Subscription Link** | `brightloop_billing` | `brightloop_finance` | `account.move.subscription_id` (`Many2one -> brightloop.subscription`) |
| **Outstanding Balance** | `account.move` | `brightloop_finance` | `inv.amount_residual` (native residual tracked against `brightloop.invoice.payment`) |
| **Portal Data Scoping** | `brightloop_core` | All modules | Controllers filter queries by `request.env.user.partner_id.id` |
| **Dashboard RPC** | `brightloop_finance` | OWL Frontend | JSON-RPC `/web/dataset/call_kw` -> `brightloop.finance.dashboard.get_dashboard_kpis()` |

