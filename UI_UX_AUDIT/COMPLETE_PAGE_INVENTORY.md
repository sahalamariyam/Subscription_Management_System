# COMPLETE PAGE INVENTORY: BRIGHTLOOP SUBSCRIPTION MANAGEMENT SYSTEM

> **Document Type:** Senior Architectural & UI/UX Audit — Document 02 / 08  
> **Auditor Role:** Senior UI/UX Auditor, Software Architect & Frontend Reverse Engineer  
> **Project Name:** Brightloop Subscription Management System  
> **Target Downstream Consumer:** Google Stitch AI (Frontend Reconstruction & Modernization)  
> **Repository Path:** `/Users/noelsabu/Documents/subcription_management_oduu /`  
> **Total Distinct Pages/Views Audited:** 35 Pages

---

## 1. Master Route & Page Inventory Matrix

| Page ID | Page Name | Primary Route / Action ID | User Role / Access | View Architecture | Parent Navigation |
|---|---|---|---|---|---|
| **PAGE 01** | Public User Login | `/web/login` | Public (Unauthenticated) | Server-rendered QWeb / Bootstrap 5 | Direct URL / Auth Redirect |
| **PAGE 02** | Customer Self-Registration | `/web/signup` | Public (Unauthenticated) | Server-rendered QWeb / Bootstrap 5 | Link from `/web/login` |
| **PAGE 03** | Password Reset Request & Token Redemption | `/web/reset_password` | Public / Token Holder | Server-rendered QWeb / Bootstrap 5 | Link from `/web/login` / Email Link |
| **PAGE 04** | Customer Portal Home Dashboard | `/my`, `/my/home` | Authenticated Customer | Server-rendered QWeb / Bootstrap 5 | Post-login redirect / Nav Header |
| **PAGE 05** | Customer Profile Management | `/my/account` | Authenticated Customer | Server-rendered QWeb Form | Portal Home / User Menu |
| **PAGE 06** | Customer Connection & Security | `/my/security` | Authenticated Customer | Server-rendered QWeb Form | Portal Home / User Menu |
| **PAGE 07** | Customer Subscriptions List | `/my/subscriptions` | Authenticated Customer | Server-rendered QWeb Table / Pager | Portal Home Card / Breadcrumbs |
| **PAGE 08** | Customer Subscription Detail | `/my/subscriptions/<id>` | Authenticated Customer | Server-rendered QWeb Card / Table | Row click from `/my/subscriptions` |
| **PAGE 09** | Customer Quotations List | `/my/quotations` | Authenticated Customer | Server-rendered QWeb Table / Pager | Portal Home Card / Empty State |
| **PAGE 10** | Customer Invoices List | `/my/invoices` | Authenticated Customer | Server-rendered QWeb Table / Pager | Portal Home Card / Subscriptions |
| **PAGE 11** | Customer Invoice Detail | `/my/invoices/<id>` | Authenticated Customer | Server-rendered QWeb Card / Table | Row click from `/my/invoices` |
| **PAGE 12** | Customer Payments List | `/my/payments` | Authenticated Customer | Server-rendered QWeb Table / Pager | Portal Home Card / Invoice Detail |
| **PAGE 13** | Financial Dashboard (Primary OWL SPA) | `action_finance_dashboard_owl` | Staff / Finance User / Admin | OWL 2 Client Action (`dashboard.js`) | Finance -> Dashboard Menu |
| **PAGE 14** | Financial Dashboard (Fallback Form View) | `action_finance_dashboard` | Staff / Finance User / Admin | Odoo Backend `<form>` View | Direct Model Action / Shell |
| **PAGE 15** | All Subscriptions List View | `action_brightloop_subscription` | Staff / Admin | Odoo Backend `<list>` View | Subscriptions -> All Subscriptions |
| **PAGE 16** | Subscription Detail Form View | `view_brightloop_subscription_form` | Staff / Admin | Odoo Backend `<form>` View + Chatter | Row click from Subscriptions List |
| **PAGE 17** | Customer Quotations List View | `action_brightloop_quotations` | Staff / Admin | Odoo Backend `<list>` View (Filtered) | Subscriptions -> Quotations |
| **PAGE 18** | Subscription Plans List View | `action_brightloop_plan` | Staff / Admin | Odoo Backend `<list>` View | Catalog & Plans -> Plans |
| **PAGE 19** | Subscription Plan Form View | `view_brightloop_plan_form` | Staff / Admin | Odoo Backend `<form>` View + Chatter | Row click from Plans List |
| **PAGE 20** | Products List View | `action_brightloop_product` | Staff / Admin | Odoo Backend `<list>` View | Catalog & Plans -> Products |
| **PAGE 21** | Product Detail Form View | `view_brightloop_product_form` | Staff / Admin | Odoo Backend `<form>` View + Chatter | Row click from Products List |
| **PAGE 22** | Quotation Templates List View | `action_brightloop_quotation_template`| Admin Only | Odoo Backend `<list>` View | Configuration -> Quotation Templates |
| **PAGE 23** | Quotation Template Form View | `view_brightloop_quotation_template_form` | Admin Only | Odoo Backend `<form>` View | Row click from Templates List |
| **PAGE 24** | Billing Jobs Audit List View | `action_brightloop_billing_job` | Admin Only | Odoo Backend `<list>` View (No Create) | Brightloop Root -> Billing Jobs |
| **PAGE 25** | Billing Job Form View | `view_brightloop_billing_job_form` | Admin Only | Odoo Backend `<form>` View (Audit) | Row click from Billing Jobs List |
| **PAGE 26** | Payments List View | `action_brightloop_payment` | Finance User / Manager | Odoo Backend `<list>` View | Finance -> Payments |
| **PAGE 27** | Payment Detail Form View | `view_payment_form` | Finance User / Manager | Odoo Backend `<form>` View + Chatter | Row click from Payments List |
| **PAGE 28** | Payment Allocations List View | `action_invoice_payment` | Finance User / Manager | Odoo Backend `<list>` View | Finance -> Payment Allocations |
| **PAGE 29** | Payment Allocation Form View | `view_invoice_payment_form` | Finance User / Manager | Odoo Backend `<form>` View | Row click from Allocations List |
| **PAGE 30** | Payment Methods List View | `action_payment_method` | Finance Manager Only | Odoo Backend Editable `<list>` View | Finance -> Config -> Payment Methods |
| **PAGE 31** | Payment Method Form View | `view_payment_method_form` | Finance Manager Only | Odoo Backend `<form>` View | Form open from Payment Methods |
| **PAGE 32** | Staff Management List View | `action_brightloop_staff_management` | Admin Only | Odoo Backend `<list>` View | Brightloop Root -> Staff Management |
| **PAGE 33** | Staff User Form View | View on `res.users` | Admin Only | Odoo Backend `<form>` View | Row click from Staff List |
| **PAGE 34** | Record Payment Wizard Modal | `action_payment_wizard` | Finance User / Manager | Odoo Backend Modal Form (`target=new`) | Finance -> Record Payment Menu |
| **PAGE 35** | Financial Report XLSX Export Modal | `action_finance_export` | Finance User / Manager | Odoo Backend Modal Form (`target=new`) | Finance -> Export Report / OWL Button |

---

## 2. Page Taxonomy & Access Hierarchy

```
BRIGHTLOOP PLATFORM NAVIGATION TREE
│
├── 🌐 PUBLIC / UNAUTHENTICATED
│   ├── [PAGE 01] /web/login (Standard Login Form)
│   ├── [PAGE 02] /web/signup (B2C Customer Self-Registration)
│   └── [PAGE 03] /web/reset_password (Anti-Enumeration Password Reset)
│
├── 👤 CUSTOMER PORTAL (Role: Customer / group_brightloop_customer)
│   ├── [PAGE 04] /my, /my/home (Portal Dashboard with Counter Cards)
│   ├── [PAGE 05] /my/account (Profile & Contact Editor)
│   ├── [PAGE 06] /my/security (Password Change with Strict Policy Validation)
│   ├── [PAGE 07] /my/subscriptions (Paginated Subscriptions List with Filters)
│   ├── [PAGE 08] /my/subscriptions/<id> (Subscription Detail, Plan & Lines)
│   ├── [PAGE 09] /my/quotations (Paginated Commercial Quotations List)
│   ├── [PAGE 10] /my/invoices (Paginated Customer Invoices with Status Filters)
│   ├── [PAGE 11] /my/invoices/<id> (Invoice Detail with Subtotal Line Items)
│   └── [PAGE 12] /my/payments (Paginated Payment History with Allocation Breakdown)
│
├── 💼 INTERNAL STAFF & BACKEND (Roles: Staff & Admin / group_brightloop_staff / group_brightloop_admin)
│   │
│   ├── 📊 FINANCE APP (menu_brightloop_finance_root)
│   │   ├── [PAGE 13] Financial Dashboard (OWL SPA: 6 KPIs, Progress Bar, Payments Table)
│   │   ├── [PAGE 14] Financial Dashboard (Fallback Form View)
│   │   ├── [PAGE 26] Payments (List View: Status decorations, Unallocated highlights)
│   │   ├── [PAGE 27] Payment Form (State machine, Invoices Notebook, Chatter)
│   │   ├── [PAGE 28] Payment Allocations (List View: Joined to account.move)
│   │   ├── [PAGE 29] Payment Allocation Form (Allocation Line Editor)
│   │   └── ⚙️ Configuration (Manager Only)
│   │       ├── [PAGE 30] Payment Methods (Editable List View)
│   │       └── [PAGE 31] Payment Method Form View
│   │
│   ├── 🔄 SUBSCRIPTIONS APP (menu_brightloop_subscription_root)
│   │   ├── Subscriptions Menu
│   │   │   ├── [PAGE 15] All Subscriptions (List View: Lifecycle Badges, Pause Toggles)
│   │   │   ├── [PAGE 16] Subscription Form (Header Workflow Buttons, Lines, Terms, Chatter)
│   │   │   └── [PAGE 17] Quotations (List View: Filtered to Draft & Quotation)
│   │   │
│   │   ├── Catalog & Plans Menu
│   │   │   ├── [PAGE 18] Subscription Plans (List View: Cadence Badges, Permissions)
│   │   │   ├── [PAGE 19] Subscription Plan Form (Cadence, Governance, Availability)
│   │   │   ├── [PAGE 20] Products (List View: Type Badges, Pricing)
│   │   │   └── [PAGE 21] Product Form (Variant Sub-Table, Price Adjustments, Chatter)
│   │   │
│   │   └── ⚙️ Configuration Menu (Admin Only)
│   │       ├── [PAGE 22] Quotation Templates (List View)
│   │       └── [PAGE 23] Quotation Template Form (Preset Lines, Plan Link)
│   │
│   └── 🛡️ BRIGHTLOOP CORE ROOT APP (menu_brightloop_root — Admin Only)
│       ├── [PAGE 24] Billing Jobs Audit (List View: Idempotency Keys, Execution Status)
│       ├── [PAGE 25] Billing Job Form (Audit Log, Execution Timestamp, Error Trace)
│       ├── [PAGE 32] Staff Management (List View: Filtered to Non-Portal Staff)
│       └── [PAGE 33] Staff User Form (Group Assignment, Credential Provisioning)
│
└── 🪟 MODALS & TRANSACTION WIZARDS
    ├── [PAGE 34] Record Payment Wizard (`brightloop.payment.wizard`)
    └── [PAGE 35] Export Financial Report Wizard (`brightloop.finance.export`)
```

