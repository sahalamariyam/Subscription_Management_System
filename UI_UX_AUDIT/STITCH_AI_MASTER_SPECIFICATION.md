# GOOGLE STITCH AI MASTER IMPLEMENTATION SPECIFICATION
## FRONTEND RECONSTRUCTION & MODERNIZATION BLUEPRINT

> **Document Type:** Master Implementation Specification — Document 07 / 08  
> **Auditor Role:** Senior UI/UX Auditor, Software Architect & Frontend Reverse Engineer  
> **Target Downstream AI:** Google Stitch AI  
> **Project:** Brightloop Subscription Management System  
> **Repository Path:** `/Users/noelsabu/Documents/subcription_management_oduu /`  
> **Date:** October 31, 2026

---

## 1. Directive for Google Stitch AI

Google Stitch AI is tasked with recreating the frontend of the **Brightloop Subscription Management System** with a state-of-the-art, visually stunning, modern design. 

### Core Instructions for Stitch AI:
1. **Never Remove Functionality:** You may redesign layouts, improve typography, create modern cards, introduce micro-interactions, and elevate aesthetics, but you **MUST NEVER remove or omit existing fields, action buttons, table columns, workflow transitions, validation rules, or role-based restrictions**.
2. **Preserve Exact Data Contracts:** All field names, API parameters, and model references must map directly to the backend contracts documented in `FUNCTIONALITY_AND_API_MAPPING.md`.
3. **Adopt Modern Design Tokens:** Implement the modern Indigo/Emerald/Slate color system, 4px spacing scale, elevation shadows, and clean typography defined in `DESIGN_SYSTEM.md`.

---

# MODULE SPECIFICATION 01: PUBLIC AUTHENTICATION & ACCESS
### Target Views: PAGE 01 (`/web/login`), PAGE 02 (`/web/signup`), PAGE 03 (`/web/reset_password`)

### 1. Page Design Brief
Transform the plain, centered Odoo login box into a modern, dual-pane enterprise authentication screen. The left pane features branded illustration and value propositions ("Automate your subscriptions and recurring billing with confidence"), while the right pane houses the sleek, minimalist authentication card with floating label inputs and smooth transitions between Login, Signup, and Reset states.

### 2. Component Inventory
- Branded illustration banner / side panel.
- Card container with subtle border (`border: 1px solid #E2E8F0`) and smooth shadow.
- Tabbed switcher or clean subtext toggle between `Log In`, `Sign Up`, and `Reset Password`.
- Form inputs: Full Name, Email Address, Password, Confirm Password.
- Password strength indicator (Visual checklist: length >= 12, uppercase, lowercase, special character).
- Primary submit button with loading spinner state.
- Security badges (PBKDF2-SHA512 encryption notice).

### 3. Content Specification
- **Login Headings:** `Welcome back`, `Sign in to manage your subscriptions and invoices`.
- **Signup Headings:** `Create your account`, `Start your customer journey with Brightloop`.
- **Reset Headings:** `Reset your password`, `Enter your registered email address to receive recovery instructions`.
- **Field Labels:** `Full Name`, `Email Address`, `Password`, `Confirm Password`.
- **Buttons:** `Sign In`, `Create Account`, `Send Reset Instructions`, `Back to Login`.
- **Generic Feedback Notice:** `"If an account exists for this email address, password reset instructions have been sent."`

### 4. Interaction Specification
- On submit, button transitions into a disabled state showing a loading spinner.
- Live client-side regex check on email field before dispatching request.
- Password field includes a show/hide toggle eye icon.
- Password strength meter updates in real-time as the user types.

### 5. Data Specification
- Endpoint: POST `/web/login`, POST `/web/signup`, POST `/web/reset_password`.
- Payload parameters: `login`, `password`, `confirm_password`, `name`, `csrf_token`.

### 6. Responsive Specification
- **Desktop (>1024px):** 50/50 split dual pane.
- **Tablet & Mobile (<1024px):** Left illustration collapses; right pane expands to full width (100%) with clean top padding.

### 7. Functional Preservation Checklist
- [x] Must enforce minimum 12-character password policy with upper, lower, and special char rules.
- [x] Must retain anti-enumeration generic message on password reset.
- [x] Must automatically assign `group_brightloop_customer` upon signup.
- [x] Must redirect customer users to `/my` and staff users to `/odoo`.

---

# MODULE SPECIFICATION 02: CUSTOMER PORTAL SELF-SERVICE HUB
### Target Views: PAGE 04 (`/my`), PAGE 05 (`/my/account`), PAGE 06 (`/my/security`)

### 1. Page Design Brief
Modernize the customer portal home into an executive self-service dashboard. Instead of basic document list items, render sleek interactive service cards with gradient accent icons, live badge counters, and rapid search/filter capabilities. The profile and security editors should feel like a contemporary SaaS settings panel.

### 2. Component Inventory
- Top navigation bar with customer organization brand switcher, user avatar, and logout dropdown.
- Quick summary hero banner with personalized greeting (`Welcome back, [Customer Name]`).
- 4 primary service cards:
  - `My Subscriptions` (with dynamic active count badge)
  - `My Quotations` (with pending offers badge)
  - `My Invoices` (with outstanding balance alert badge)
  - `My Payments` (with total payment count badge)
- Profile management drawer or 2-column card layout (`Personal Details` and `Billing Address`).
- Security panel with password change form.

### 3. Content Specification
- **Subscriptions Card:** `My Subscriptions`, `View running recurring plans, renewal cadences, and service status`.
- **Quotations Card:** `My Quotations`, `Review pending subscription proposals, pricing quotes, and accept terms`.
- **Invoices Card:** `My Invoices`, `Inspect monthly statements, tax breakdown, and payment status`.
- **Payments Card:** `My Payments`, `View transaction history, payment receipts, and applied invoice allocations`.
- **Profile Fields:** `Customer Name`, `Email Address`, `Phone`, `Street Address`, `Street 2`, `City`, `Postal / Zip Code`, `Country`, `State / Province`.

### 4. Interaction & Data Specification
- Data sources: `_prepare_home_portal_values()` providing `subscription_count`, `invoice_count`, `payment_count`.
- Profile updates submit via POST `/my/account` with IDOR protection bound to `request.env.user.partner_id`.
- Duplicate email check returns inline error without clearing other form fields.

### 5. Functional Preservation Checklist
- [x] Customer must only see counters and records belonging to their partner (`child_of user.commercial_partner_id.id`).
- [x] Profile cannot expose or edit internal fields (`share`, `groups_id`).

---

# MODULE SPECIFICATION 03: CUSTOMER PORTAL LISTS & DETAILS
### Target Views: PAGE 07, 08, 09, 10, 11, 12 (`/my/subscriptions`, `/my/invoices`, etc.)

### 1. Page Design Brief
Design high-clarity data tables featuring rounded corners, subtle row borders, hover highlights, and dedicated status badge components. Detail views must render as rich commercial summary invoices with breadcrumb navigation, plan specification chips, and clear outstanding balance callouts.

### 2. Component Inventory
- Sub-navigation filter pills:
  - Subscriptions: `All Active`, `Running`, `Paused`.
  - Invoices: `All`, `Unpaid`, `Paid`, `Overdue`.
- Sort dropdown: `Newest First`, `Oldest First`, `Reference / Name`.
- Full-width responsive data table with sticky header.
- Custom status badges:
  - Active: Emerald pill (`bg-emerald-50 text-emerald-700 border-emerald-200`)
  - Paused: Cyan pill (`bg-cyan-50 text-cyan-700 border-cyan-200`)
  - Quotation: Amber pill (`bg-amber-50 text-amber-700 border-amber-200`)
  - Overdue Invoice: Rose pill (`bg-rose-50 text-rose-700 border-rose-200`)
- Detail cards displaying 2-column key-value metrics and itemized line-item tables with quantity, unit price, and subtotal.
- Pagination bar with page counter and jump-to-page controls.

### 3. Functional Preservation Checklist
- [x] Subscriptions table must display `Reference`, `Plan`, `Status`, `Start Date`, `Next Billing Date`, and `Action`.
- [x] Invoices table must display `Invoice #`, `Date`, `Due Date`, `Total`, `Outstanding`, `Status`, and `Action`.
- [x] Payments table must display `Reference`, `Method`, `Date`, `Amount`, `Allocated`, and `Unallocated`.
- [x] Overdue invoices must highlight due dates and outstanding amounts in red/rose.
- [x] Subscription detail must link to linked invoices, and invoice detail must cross-link to linked subscription.

---

# MODULE SPECIFICATION 04: EXECUTIVE FINANCIAL DASHBOARD (OWL SPA)
### Target View: PAGE 13 (`action_finance_dashboard_owl`)

### 1. Page Design Brief
Recreate the OWL 2 single-page financial dashboard into a top-tier C-level financial command center. Features clean metric cards with micro-charts, an interactive date-range picker, a unified collection rate card with visual progress ring or bar, a clean transaction ledger table, and prominent XLSX report generation.

### 2. Component Inventory
- Sticky dashboard header bar with brand title and quick-date presets (`This Month`, `Last Month`, `Year to Date`, `Custom Range`).
- From & To date inputs with `Apply` and `Reset` buttons.
- 6 Key Performance Indicator (KPI) Metric Cards:
  1. `Active Subscriptions`: Emerald icon, large bold count.
  2. `Paused Subscriptions`: Cyan icon, large bold count.
  3. `Revenue Received`: Indigo icon, formatted USD currency (`$XX,XXX.XX`).
  4. `Total Invoiced`: Slate icon, formatted USD currency.
  5. `Outstanding Balance`: Amber icon, formatted USD currency.
  6. `Overdue Invoices`: Rose icon, bold count with subtitle displaying total overdue monetary sum.
- Collection Rate Card: Progress bar displaying percentage of invoiced revenue successfully collected (`revenue_received / total_invoiced * 100`).
- Recent Payments Table: 20 most recent payments with columns for Reference, Customer, Method, Total Amount, Allocated, Unallocated, and Date.
- Action Toolbar: `Export to XLSX` button and `Refresh` button.

### 3. Interaction & RPC Specification
- On component mount or date change, call JSON-RPC:
  ```javascript
  const result = await this.rpc("/web/dataset/call_kw", {
      model: "brightloop.finance.dashboard",
      method: "get_dashboard_kpis",
      args: [this.state.dateFrom, this.state.dateTo],
      kwargs: {},
  });
  ```
- Export XLSX button invokes `brightloop.finance.export.export_xlsx`, decodes binary base64 stream, triggers automatic browser file download, and fires success toast.

### 4. Functional Preservation Checklist
- [x] Must dynamically compute all 6 KPIs using date-filtered parameters.
- [x] Must support collection rate calculation.
- [x] Must load last 20 payments with unallocated amounts highlighted.
- [x] Must trigger client-side base64 binary download of formatted 6-sheet XLSX report.

---

# MODULE SPECIFICATION 05: SUBSCRIPTION MANAGEMENT & LIFECYCLE STUDIO
### Target Views: PAGE 15 (List) & PAGE 16 (Form)

### 1. Page Design Brief
Transform the subscription form into a comprehensive commercial command studio. The form header must cleanly organize the 8 lifecycle buttons with intelligent grouping (e.g., primary action highlighted, secondary actions in dropdown or button group) to eliminate visual clutter. The document sheet displays status ribbons, plan terms, and a dynamic subscription lines editor.

### 2. Component Inventory
- Action Header with Lifecycle Workflow Buttons:
  - `Send Quotation` (Draft stage)
  - `Confirm Order` (Quotation stage)
  - `Reset to Draft` (Quotation stage)
  - `Activate Subscription` (Confirmed stage)
  - `Pause Subscription` (Active stage, when not paused)
  - `Resume Subscription` (Active stage, when paused)
  - `Renew Subscription` (Active stage)
  - `Close Subscription` (Active or Confirmed stage)
  - Statusbar Widget (`draft -> quotation -> confirmed -> active -> closed`)
- Ribbons: Warning `"Paused"` and Danger `"Closed"`.
- Form Header: Large subscription number (`SUB/YYYY/NNNNN`).
- 2-Column Attributes Card:
  - Group 1: `Customer` (`partner_id`), `Plan` (`plan_id`), `Quotation Template` (`template_id`), `Company` (`company_id`).
  - Group 2: `Valid Until`, `Start Date`, `Expiry Date`, `Next Billing Date`, `Billing Interval`, `Interval Count`, `Renewal Count`.
- Closure Details Section (conditional on Closed status): `Closed Date`, `Closure Reason`, `Early Closed`.
- Notebook Tabs:
  - Tab 1 (`Subscription Lines`): Inline editable list (`product_id`, `variant_id`, `name`, `quantity`, `unit_price`, `discount`, `discount_id`, `tax_id`, `amount_subtotal`), Subtotal and Total footer.
  - Tab 2 (`Commercial Terms`): `payment_terms` string field.
- Odoo Mail Chatter widget.

### 3. Functional Preservation Checklist
- [x] Must enforce minimum quantity validation on quotation transition.
- [x] Must enforce quotation expiration check on confirmation.
- [x] Must preserve 31st anchor-day billing date advancement on activation and renewal.
- [x] Must enforce plan governance flags: `allow_pause`, `allow_renewal`, `allow_early_close`.
- [x] Must advance dates and increment renewal count on renewal.

---

# MODULE SPECIFICATION 06: CATALOG, PLANS & RECURRING BILLING ENGINE
### Target Views: PAGE 18, 19 (Plans), PAGE 20, 21 (Products), PAGE 24, 25 (Billing Jobs)

### 1. Page Design Brief
Modernize product and plan management with clean cards, interval badges, and governance toggle switches. Billing jobs must render as an immutable execution ledger with status indicators, execution timings, and error trace view.

### 2. Component Inventory & Preserved Features
- **Subscription Plans Form:**
  - Name, `billing_price`, `billing_interval` (Daily, Weekly, Monthly, Yearly), `billing_interval_count`, `minimum_quantity`.
  - Date window: `start_date`, `end_date`.
  - Governance Toggles: `allow_pause`, `allow_renewal`, `allow_early_close`, `auto_close`.
- **Products & Variants Form:**
  - Name, `product_type` (Software, Add-on, Service), `sales_price`, `cost_price`.
  - Variants Table: `name`, `price_adjustment`, `effective_price` (`sales_price + price_adjustment`).
- **Billing Jobs Ledger:**
  - Readonly immutable table displaying `subscription_id`, `invoice_id`, `billing_period_start`, `billing_period_end`, `idempotency_key`, `state` (`pending`, `done`, `failed`), `attempted_at`, `completed_at`, `error_message`.
  - Stat button to navigate directly to the generated `account.move` customer invoice.

---

# MODULE SPECIFICATION 07: FINANCIAL PAYMENT WIZARD & EXPORT MODALS
### Target Views: PAGE 34 (`brightloop.payment.wizard`) & PAGE 35 (`brightloop.finance.export`)

### 1. Page Design Brief
Modernize modal dialogs with clear 2-step progress or wizard stepper headers, smooth backdrop blur, responsive input grids, and live calculation summaries.

### 2. Payment Recording Wizard Specification
- **Step 1 (Customer & Funds):** Select `partner_id`, `payment_method_id`, `amount`, `payment_date`, `reference`, `notes`.
- **Step 2 (Invoice Allocation):** Dynamic sub-table populated with open invoices for the chosen customer. Columns: `Invoice #`, `Due Date`, `Invoice Total`, `Balance Due`, `Allocate Amount`.
- **Live Summary Bar:** Displays `Total Allocated` and `Remaining Unallocated`.
- **Confirmation Action:** Creates `brightloop.payment` and `brightloop.invoice.payment` records in a single database transaction. Prevents over-allocation against balance due.

### 3. Financial XLSX Export Specification
- **Configuration View:** Select Date Range (`date_from`, `date_to`), optional filters for `partner_id` and `subscription_id`, select `export_type` (Full Report, Payments, Invoices, Outstanding, Overdue, Revenue Summary, Subscriptions).
- **Download View:** Renders success banner and direct download button for the generated `.xlsx` spreadsheet.
- **Workbook Architecture:** Generates 6 fully formatted sheets using `xlsxwriter` with custom header banners, currency formats, and summary totals rows.

