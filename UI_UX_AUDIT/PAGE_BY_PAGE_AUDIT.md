# PAGE-BY-PAGE UI AUDIT: BRIGHTLOOP SUBSCRIPTION MANAGEMENT SYSTEM

> **Document Type:** Senior Architectural & UI/UX Audit — Document 03 / 08  
> **Auditor Role:** Senior UI/UX Auditor, Software Architect & Frontend Reverse Engineer  
> **Project Name:** Brightloop Subscription Management System  
> **Target Downstream Consumer:** Google Stitch AI (Frontend Reconstruction & Modernization)  
> **Repository Path:** `/Users/noelsabu/Documents/subcription_management_oduu /`  
> **Audit Date:** October 31, 2026  
> **Coverage:** 35 Distinct Application Pages, Views, Modals & Components

---

# SECTION 1: PUBLIC & AUTHENTICATION INTERFACES

---

## PAGE 01: Public User Login
### A. Page Identification
- **Page ID:** PAGE 01
- **Page Name:** User Login
- **Route / URL:** `/web/login`
- **Page Purpose:** Authenticate returning customers and internal staff into their respective portal and backend environments.
- **Intended User:** Unauthenticated visitors, registered customers, staff members, administrators.
- **Authentication Requirement:** Public (None).
- **Parent Page / Navigation Path:** Standalone landing URL or redirected from any protected route (`/my`, `/odoo`).
- **Display Mode:** Standalone full-page web interface.

### B. Overall Page Layout
- **Visual Structure:** Vertically and horizontally centered login card container on a neutral light background (`#f8f9fa`).
- **Header:** Odoo / Brightloop brand logo centered at the top of the card.
- **Main Area:** Stacked login credentials form.
- **Footer Section:** Auxiliary links for password recovery and customer signup.

### C. Every UI Component
| Component Name | Component Type | Position | Purpose | Label | Behaviour | Data Dependency | Navigation | State |
|---|---|---|---|---|---|---|---|---|
| `login_card` | Container Card | Center viewport | Houses authentication form | N/A | Static container | None | None | Visible |
| `input_email` | Text Input | Upper form | Accepts login identifier | `Email` | User text entry | `login` (email) | None | Enabled |
| `input_password` | Password Input | Middle form | Accepts cleartext password | `Password` | Masks characters | `password` | None | Enabled |
| `btn_submit` | Primary Button | Lower form | Submits credentials | `Log in` | POST to `/web/login` | Form data | Redirects on success | Enabled |
| `link_reset` | Anchor Link | Bottom card | Navigates to reset flow | `Reset Password` | Navigates to `/web/reset_password` | None | `/web/reset_password` | Enabled |
| `link_signup` | Anchor Link | Bottom card | Navigates to registration | `Don't have an account? Sign up`| Navigates to `/web/signup` | None | `/web/signup` | Enabled |

### D. Buttons & Interactive Elements
- **`Log in` (Primary Button):** Triggers form submission. Validates fields client-side, initiates POST to `/web/login`. If authenticated as customer, redirects to `/my`; if staff/admin, redirects to `/odoo`.
- **`Reset Password` (Link):** Directs visitor to the password recovery screen.
- **`Sign up` (Link):** Directs visitor to the B2C self-service registration screen.

### E. Forms & Input Fields
1. **Form Name:** `login_form`
2. **Action / Target:** POST to `/web/login`
3. **Fields:**
   - `login`: Input text/email, placeholder: `Email`, required, autocomplete `username`.
   - `password`: Input password, placeholder: `Password`, required, autocomplete `current-password`.
   - `csrf_token`: Hidden input, system security token.
4. **Validation Rules:** Non-empty string checks on client; server validates against database hash.
5. **Error Messages:** Alert banner displaying `Wrong login/password` on authentication failure.

---

## PAGE 02: Customer Self-Registration
### A. Page Identification
- **Page ID:** PAGE 02
- **Page Name:** Customer Self-Registration / Signup
- **Route / URL:** `/web/signup`
- **Page Purpose:** Allow external consumers to register a customer account with automatic assignment of `group_brightloop_customer`.
- **Intended User:** Unauthenticated prospective customers.
- **Authentication Requirement:** Public (None).
- **Parent Page / Navigation Path:** Linked from `/web/login`.
- **Display Mode:** Standalone centered card.

### B. Overall Page Layout
- **Visual Structure:** Card-centered form layout matching the authentication design language.
- **Header:** Brightloop brand logo, subtitle text `Create your customer account`.
- **Main Area:** Multi-field registration form including live password policy requirements.
- **Footer:** Link back to login (`Already have an account? Log in`).

### C. Every UI Component
| Component Name | Component Type | Position | Purpose | Label | Behaviour | Data Dependency | Navigation | State |
|---|---|---|---|---|---|---|---|---|
| `signup_card` | Container Card | Center viewport | Encloses registration inputs | N/A | Static | None | None | Visible |
| `input_name` | Text Input | Form top | Full name / Org name | `Your Name` | Text entry | `name` | None | Enabled |
| `input_login` | Email Input | Form row 2 | Customer email address | `Your Email` | Text entry | `login` | None | Enabled |
| `input_password` | Password Input | Form row 3 | Account password | `Password` | Masks entry | `password` | None | Enabled |
| `input_confirm` | Password Input | Form row 4 | Re-enter password | `Confirm Password` | Masks entry | `confirm_password` | None | Enabled |
| `policy_help` | Text Banner | Below passwords | Explains password rules | Policy guidelines | Informational text | None | None | Static |
| `btn_signup` | Primary Button | Form bottom | Submits account data | `Sign up` | POST to `/web/signup` | Form fields | Redirects to `/my` | Enabled |

### D. Buttons & Interactive Elements
- **`Sign up` (Primary Submit Button):** Submits form payload to server.
- **`Back to Login` (Anchor Link):** Navigates back to `/web/login`.

### E. Forms & Input Fields
1. **Form Name:** `signup_form`
2. **Action / Target:** POST to `/web/signup`
3. **Fields:**
   - `name`: Mandatory, string, min length 2.
   - `login`: Mandatory, valid email regex (`^[^@\s]+@[^@\s]+\.[^@\s]+$`).
   - `password`: Mandatory, validated by `_validate_password_policy` (length >= 12, uppercase, lowercase, special character).
   - `confirm_password`: Mandatory, must match `password` identically.
4. **Error Handling:**
   - "Passwords do not match; please retype them."
   - "Please provide a valid email address."
   - "Another user is already registered using this email address."
   - "Password must be at least 12 characters long and include uppercase, lowercase, and special characters."

---

## PAGE 03: Password Reset Request & Token Redemption
### A. Page Identification
- **Page ID:** PAGE 03
- **Page Name:** Password Reset (Two-Stage)
- **Route / URL:** `/web/reset_password`
- **Page Purpose:** Stage 1: Request reset email (anti-enumeration protected). Stage 2: Enter new password with valid cryptographic HMAC token.
- **Intended User:** Users who forgot their password or received a password reset invitation.
- **Authentication Requirement:** Public (None).
- **Parent Page / Navigation Path:** `/web/login` -> Reset Password link, or direct email link.
- **Display Mode:** Centered card interface.

### B. Overall Page Layout
- **Visual Structure:** Card container displaying email input in Stage 1, or new password + confirmation inputs in Stage 2.
- **Header:** Brand logo, title `Reset Password`.
- **Main Area:** Dynamic form depending on presence of `?token=...` in query parameters.
- **Alert Section:** Dynamic alert displaying success confirmation or error message.

### C. Every UI Component
| Component Name | Component Type | Position | Purpose | Label | Behaviour | Data Dependency | Navigation | State |
|---|---|---|---|---|---|---|---|---|
| `stage1_email` | Text Input | Form body (No token) | User email | `Your Email` | Text entry | `login` | None | Visible if no token |
| `stage1_submit`| Primary Button | Form bottom (No token) | Request reset link | `Confirm` | POST email | Form data | None | Enabled |
| `stage2_pass` | Password Input | Form body (Token active)| New password | `New Password` | Masked text | `password` | None | Visible if token |
| `stage2_confirm`| Password Input| Form body (Token active)| Verify password | `Confirm Password` | Masked text | `confirm_password` | None | Visible if token |
| `stage2_submit`| Primary Button | Form bottom (Token active)| Save new password | `Reset Password` | Submits token & pass | Database | Redirects to `/my` | Enabled |
| `msg_alert` | Alert Box | Top of form | Feedback notice | Status message | Display message | `qcontext['message']` | None | Conditional |

### D. Forms & Validation Rules
- **Anti-Enumeration Guarantee:** Regardless of whether the submitted email exists in `res.users`, the server displays: `"If an account exists for this email address, password reset instructions have been sent."`
- **Token Invalidation:** Token is cryptographically validated and immediately revoked (`signup_type = False`) upon successful reset to prevent replay attacks.

---

# SECTION 2: CUSTOMER SELF-SERVICE PORTAL

---

## PAGE 04: Customer Portal Home Dashboard
### A. Page Identification
- **Page ID:** PAGE 04
- **Page Name:** Customer Portal Home
- **Route / URL:** `/my`, `/my/home`
- **Page Purpose:** Primary self-service hub for authenticated customers to overview their subscriptions, quotations, invoices, payments, and account profile.
- **Intended User:** Authenticated Customer (`brightloop_core.group_brightloop_customer`).
- **Authentication Requirement:** Mandatory (`auth='user'`).
- **Parent Page / Navigation Path:** Post-authentication landing page.
- **Display Mode:** Portal web layout with navigation header, sidebar cards, and document cards grid.

### B. Overall Page Layout
- **Header:** Sticky Odoo Portal navigation bar with breadcrumbs (`Home`), user display name dropdown, and company branding.
- **Main Area:** 2-column or 3-column card grid displaying operational service cards with live badges and counters.
- **Sidebar / User Panel:** Quick contact summary, links to `Edit Profile` (`/my/account`) and `Security` (`/my/security`).

### C. Every UI Component
| Component Name | Component Type | Position | Purpose | Label | Behaviour | Data Dependency | Navigation | State |
|---|---|---|---|---|---|---|---|---|
| `nav_portal` | Navbar | Top sticky | Brand navigation | `Brightloop` | Global navigation | Session | Various | Static |
| `user_dropdown` | Dropdown Menu | Top right | Profile actions | User Name | Opens user menu | `request.env.user` | `/my/account`, `/web/session/logout` | Enabled |
| `card_subscriptions` | Action Card | Main grid | Access active subs | `My Subscriptions` | Navigates to subs | `subscription_count` | `/my/subscriptions` | Enabled |
| `badge_sub_count` | Numerical Badge | Card header | Active sub counter | Numerical count | Displays total active | `subscription_count` | None | Visible |
| `card_quotations` | Action Card | Main grid | Access pending quotes| `My Quotations` | Navigates to quotes | None | `/my/quotations` | Enabled |
| `card_invoices` | Action Card | Main grid | Access billing invoices| `My Invoices` | Navigates to invoices | `invoice_count` | `/my/invoices` | Enabled |
| `badge_inv_count` | Numerical Badge | Card header | Posted invoice counter| Numerical count | Displays posted invoices | `invoice_count` | None | Visible |
| `card_payments` | Action Card | Main grid | Access receipts | `My Payments` | Navigates to payments | `payment_count` | `/my/payments` | Enabled |
| `badge_pay_count` | Numerical Badge | Card header | Posted payment count | Numerical count | Displays payment count | `payment_count` | None | Visible |

### D. Navigation & Interactive Flow
- Clicking any card redirects the customer to the respective paginated list view with server-side record isolation applied.

---

## PAGE 05: Customer Profile Management
### A. Page Identification
- **Page ID:** PAGE 05
- **Page Name:** Customer Profile Editor
- **Route / URL:** `/my/account`
- **Page Purpose:** Permit customers to view and update authorized contact and billing address details.
- **Intended User:** Authenticated Customer.
- **Authentication Requirement:** Mandatory (`auth='user'`).
- **Parent Page / Navigation Path:** `/my/home` -> User Menu -> `My Account`.
- **Display Mode:** Form within portal page layout.

### B. Overall Page Layout
- **Header:** Breadcrumbs: `Home / Your Details`.
- **Main Area:** Two-column responsive contact information form.
- **Footer:** Save button (`Confirm`) and Cancel link.

### C. Every UI Component & Input Field
| Field Name | Input Type | Required | Label | Default Value | Validation / Protection |
|---|---|---|---|---|---|
| `name` | Text | Yes | `Name` | `partner.name` | Mandatory string |
| `email` | Email | Yes | `Email` | `partner.email` | Regex syntax + duplicate account collision check |
| `phone` | Tel | No | `Phone` | `partner.phone` | Valid phone format |
| `street` | Text | No | `Street` | `partner.street` | Alphanumeric |
| `street2` | Text | No | `Street 2` | `partner.street2` | Alphanumeric |
| `city` | Text | No | `City` | `partner.city` | Alphabetic |
| `zipcode` | Text | No | `Zip Code` | `partner.zip` | Postal code format |
| `country_id` | Select Dropdown| No | `Country` | `partner.country_id.id` | Filtered list of active countries |
| `state_id` | Select Dropdown| No | `State / Province` | `partner.state_id.id` | Filtered list dependent on `country_id` |

### D. Security & Data Protection
- **IDOR Protection:** Payload `partner_id` parameter is ignored; updates bind strictly to `request.env.user.partner_id`.
- **Protected Fields:** Internal classification (`share`), groups (`groups_id`), accounting terms, and credit limits cannot be modified by customer.

---

## PAGE 06: Customer Connection & Security
### A. Page Identification
- **Page ID:** PAGE 06
- **Page Name:** Connection & Security Settings
- **Route / URL:** `/my/security`
- **Page Purpose:** Allow authenticated customers to change their login password with strict password policy enforcement.
- **Intended User:** Authenticated Customer.
- **Authentication Requirement:** Mandatory (`auth='user'`).
- **Display Mode:** Form within portal layout.

### B. Input Fields & Validation
- `old_password`: Current password, required, authenticated against database.
- `new_password`: New password, required, validated against policy (length >= 12, uppercase, lowercase, special character).
- `confirm_password`: Password confirmation, must match `new_password`.

---

## PAGE 07: Customer Subscriptions List
### A. Page Identification
- **Page ID:** PAGE 07
- **Page Name:** Customer Subscriptions List
- **Route / URL:** `/my/subscriptions`, `/my/subscriptions/page/<int:page>`
- **Page Purpose:** Display all confirmed and active recurring subscriptions belonging to the logged-in customer.
- **Intended User:** Authenticated Customer.
- **Authentication Requirement:** Mandatory (`auth='user'`).
- **Parent Page / Navigation Path:** `/my/home` -> `My Subscriptions` card.
- **Display Mode:** Full-width responsive table with filter and sort bars.

### B. Overall Page Layout
- **Top Bar:** Search bar, filter pills, and sort controls.
- **Filters Available:** `All Active` (`status in ['active', 'confirmed']`), `Running` (`status = 'active' and is_paused = False`), `Paused` (`status = 'active' and is_paused = True`).
- **Sort Options:** `Newest First` (`create_date desc`), `Oldest First` (`create_date asc`), `Name` (`name asc`).
- **Table Area:** Responsive Bootstrap table (`table-hover`).
- **Footer:** Odoo portal pager pagination controls (`step = 10`).

### C. Table Columns & Data Displays
| Column Header | Field Source | Data Type | Visual Representation |
|---|---|---|---|
| `Reference` | `sub.name` | Char | Semibold primary text (e.g., `SUB/2026/00088`) |
| `Plan` | `sub.plan_id.name` | Char | Plain text plan title |
| `Status` | `sub.status`, `sub.is_paused`| Selection / Boolean | Status badge macro (Green `Active`, Blue `Confirmed`, Cyan `Paused`) |
| `Start Date` | `sub.start_date` | Date | Formatted date string (`YYYY-MM-DD`) |
| `Next Billing` | `sub.next_billing_date` | Date | Text-end aligned date string |
| `Actions` | N/A | Link Button | `View` button (`btn-sm btn-outline-primary`) navigating to `/my/subscriptions/<id>` |

### D. Empty State
- Displays inbox icon (`fa-inbox fa-3x text-muted`), title `No subscriptions found.`, and primary button linking to `/my/quotations`.

---

## PAGE 08: Customer Subscription Detail View
### A. Page Identification
- **Page ID:** PAGE 08
- **Page Name:** Customer Subscription Detail
- **Route / URL:** `/my/subscriptions/<int:sub_id>`
- **Page Purpose:** Provide comprehensive commercial breakdown of an individual subscription for the customer.
- **Intended User:** Authenticated Customer (verified against `partner_id = user.partner_id.id`).
- **Display Mode:** Detailed card container with breadcrumbs.

### B. Layout & Sections
- **Breadcrumbs:** `Home / My Subscriptions / SUB/2026/00088`.
- **Card Header:** Subscription reference title + status badge.
- **Card Body:** 2-column key-value attribute grid:
  - Column 1: Plan Name, Start Date, Expiry Date, Next Billing Date.
  - Column 2: Product Name, Quantity, Unit Price.
- **Commercial Notes:** Free-form text block displaying terms or special customer notes.
- **Card Footer:** Action buttons:
  - `Back to Subscriptions` (`btn-outline-secondary` -> `/my/subscriptions`).
  - `View Invoices` (`btn-outline-primary` -> `/my/invoices`).

---

## PAGE 09: Customer Quotations List
### A. Page Identification
- **Page ID:** PAGE 09
- **Page Name:** Customer Quotations List
- **Route / URL:** `/my/quotations`, `/my/quotations/page/<int:page>`
- **Page Purpose:** Display all commercial offers and draft proposals awaiting customer acceptance.
- **Intended User:** Authenticated Customer.
- **Authentication Requirement:** Mandatory (`auth='user'`).
- **Domain Filter:** `[('partner_id', '=', partner.id), ('status', 'in', ['draft', 'quotation'])]`.
- **Display Mode:** Paginated table.

### B. Table Columns
- `Reference`: `sub.name`.
- `Plan`: `sub.plan_id.name`.
- `Status`: Badge macro (`Draft` in secondary, `Quotation` in warning).
- `Created`: `sub.create_date`.
- `Action`: `View` button linking to detail page.

---

## PAGE 10: Customer Invoices List
### A. Page Identification
- **Page ID:** PAGE 10
- **Page Name:** Customer Invoices List
- **Route / URL:** `/my/invoices`, `/my/invoices/page/<int:page>`
- **Page Purpose:** View all customer invoices generated for subscription cycles.
- **Intended User:** Authenticated Customer.
- **Domain Filter:** `[('partner_id', '=', partner.id), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]`.
- **Filter Tabs:** `All`, `Unpaid` (`payment_state not in ['paid', 'reversed']`), `Paid` (`payment_state = 'paid'`), `Overdue` (Unpaid and `invoice_date_due < today`).

### B. Table Columns & Data Displays
| Column Header | Field Source | Data Type | Formatting & Behaviour |
|---|---|---|---|
| `Invoice #` | `inv.name` | Char | Semibold primary text |
| `Date` | `inv.invoice_date` | Date | Standard formatted date |
| `Due Date` | `inv.invoice_date_due`| Date | Highlighted red if overdue and unpaid |
| `Total` | `inv.amount_total` | Float | Currency formatted (`$%.2f`) |
| `Outstanding` | `inv.amount_residual` | Float | Currency formatted; highlighted red if residual > 0 |
| `Status` | `inv.payment_state` | Selection | Badges: `Paid` (Green), `Partial` (Yellow), `In Payment` (Cyan), `Unpaid` (Red) |
| `Action` | N/A | Button | `View` button navigating to `/my/invoices/<id>` |

---

## PAGE 11: Customer Invoice Detail View
### A. Page Identification
- **Page ID:** PAGE 11
- **Page Name:** Customer Invoice Detail
- **Route / URL:** `/my/invoices/<int:invoice_id>`
- **Page Purpose:** Display complete line-item breakdown of an individual customer invoice.
- **Intended User:** Authenticated Customer.
- **Display Mode:** Detailed card container with invoice lines table.

### B. Layout & Data Sections
- **Header:** Invoice number + payment status badge (`Paid`, `Partial`, `Unpaid`).
- **Dates & Links:** Invoice date, due date, linked subscription anchor (`/my/subscriptions/<subscription_id>`).
- **Financial Highlight:** Large display metric showing Total Invoiced and Outstanding Residual.
- **Invoice Line Items Table:**
  - `Description` (`line.name`)
  - `Qty` (`line.quantity`)
  - `Unit Price` (`line.price_unit`)
  - `Subtotal` (`line.price_subtotal`)
- **Footer Buttons:** `Back to Invoices` (`/my/invoices`), `View Payments` (`/my/payments`).

---

## PAGE 12: Customer Payments List
### A. Page Identification
- **Page ID:** PAGE 12
- **Page Name:** Customer Payment History
- **Route / URL:** `/my/payments`, `/my/payments/page/<int:page>`
- **Page Purpose:** Display all confirmed payments recorded against the customer's account.
- **Intended User:** Authenticated Customer.
- **Domain Filter:** `[('partner_id', '=', partner.id), ('state', '=', 'posted')]`.

### B. Table Columns
| Column Header | Field Source | Description |
|---|---|---|
| `Reference` | `pmt.name`, `pmt.reference` | Payment sequence reference + transaction ID |
| `Method` | `pmt.payment_method_id.name` | Badge showing payment method (Card, Bank, UPI, etc.) |
| `Date` | `pmt.payment_date` | Date payment was recorded |
| `Amount` | `pmt.amount` | Total received amount |
| `Allocated` | `pmt.total_allocated` | Amount applied against invoices (Green) |
| `Unallocated` | `pmt.unallocated_amount` | Remaining credit / unapplied amount (Yellow if > 0) |

---

# SECTION 3: INTERNAL STAFF & ADMINISTRATIVE INTERFACES

---

## PAGE 13: Financial Dashboard (Primary OWL SPA Component)
### A. Page Identification
- **Page ID:** PAGE 13
- **Page Name:** Financial Dashboard
- **Component Identifier:** `brightloop_finance.FinanceDashboard` (OWL 2)
- **Action ID:** `action_finance_dashboard_owl` (`ir.actions.client`)
- **Route / Access:** Odoo Backend Web Client -> **Finance → Dashboard**
- **Intended User:** Internal Staff (`group_brightloop_staff`), Finance Users, Administrators.
- **Authentication Requirement:** Authenticated Internal User.
- **Display Mode:** Full-viewport Single-Page Application (SPA) client action.

### B. Overall Page Layout
```
+---------------------------------------------------------------------------------------+
| [fa-chart-line] Brightloop Financial Dashboard    | From [YYYY-MM-DD] To [YYYY-MM-DD] |
|                                                   | [Apply] [Reset]                   |
+---------------------------------------------------------------------------------------+
|  [Active Subs]  |  [Paused Subs]  |  [Revenue]  |  [Invoiced]  |  [Outstanding] | [Overdue] |
|       14        |        2        |  $45,200.00 |  $52,000.00  |   $6,800.00    |  3 ($1.2k)|
+---------------------------------------------------------------------------------------+
| Collection Rate: 87%                                                                  |
| [====================================================..........]                      |
| Received: $45,200.00                                               Invoiced: $52,000.00|
+---------------------------------------------------------------------------------------+
| [fa-credit-card] Recent Payments (Last 20 Records)                                    |
| Reference    | Customer       | Method | Amount     | Allocated  | Unallocated| Date      |
| PAY/2026/01  | Acme Corp      | Card   | $1,200.00  | $1,200.00  | $0.00      | 2026-10-30|
+---------------------------------------------------------------------------------------+
|                                                          [Export to XLSX] [Refresh]   |
+---------------------------------------------------------------------------------------+
```

### C. Every UI Component & Interactive Element
1. **Header Bar:**
   - Icon: `fa-chart-line fa-lg text-primary`.
   - Title: `Brightloop Financial Dashboard` (bold, letter-spacing -0.3px).
   - Date From Input: `<input type="date" class="bl-date-from">`, default first day of current month.
   - Date To Input: `<input type="date" class="bl-date-to">`, default current day.
   - `Apply` Button (`btn-primary btn-sm`): Calls `loadKPIs()` via JSON-RPC.
   - `Reset` Button (`btn-outline-secondary btn-sm`): Resets dates to defaults and reloads data.
2. **KPI Metrics Grid (6 Responsive Cards):**
   - **Card 1 (Active Subscriptions):** Left accent green (`#198754`), icon `fa-check-circle`, value `state.kpis.active_subscription_count`.
   - **Card 2 (Paused Subscriptions):** Left accent cyan (`#0dcaf0`), icon `fa-pause-circle`, value `state.kpis.paused_subscription_count`.
   - **Card 3 (Revenue Received):** Left accent blue (`#0d6efd`), icon `fa-dollar`, formatted currency `state.kpis.revenue_received`.
   - **Card 4 (Total Invoiced):** Icon `fa-file-text-o`, formatted currency `state.kpis.total_invoice_value`.
   - **Card 5 (Outstanding Balance):** Left accent yellow (`#ffc107`), icon `fa-clock-o`, formatted currency `state.kpis.total_outstanding`.
   - **Card 6 (Overdue Invoices):** Left accent red (`#dc3545`), icon `fa-exclamation-triangle`, count `state.kpis.overdue_invoice_count`, subtext displaying formatted overdue amount `state.kpis.overdue_amount`.
3. **Collection Rate Card:**
   - Calculation: `(revenue_received / total_invoice_value) * 100` clamped to 100%.
   - Progress Bar: Height 10px, smooth CSS transition (`width 0.6s ease`).
   - Summary captions displaying received vs invoiced figures.
4. **Recent Payments Table:**
   - Table of 20 most recent posted payments in the selected date window.
   - Empty state: `No payments in the selected date range.`
   - Columns: `Reference`, `Customer`, `Method`, `Amount`, `Allocated`, `Unallocated`, `Date`.
5. **Action Buttons:**
   - `Export to XLSX` (`btn-outline-primary btn-sm`): Dispatches RPC call to `brightloop.finance.export.export_xlsx`, decodes base64 payload in browser memory, and triggers direct file download with toast notification.
   - `Refresh` (`btn-outline-secondary btn-sm`): Reloads KPI state.

---

## PAGE 14: Financial Dashboard (Fallback Form View)
- **Page ID:** PAGE 14
- **Action ID:** `action_finance_dashboard`
- **Model:** `brightloop.finance.dashboard`
- **Description:** Server-rendered form view designed as a fallback for non-JavaScript or administrative backend clients. Mirrors the 7 KPIs using computed fields inside a standard Odoo `<sheet>`.

---

## PAGE 15: All Subscriptions List View
### A. Page Identification
- **Page ID:** PAGE 15
- **Page Name:** Subscriptions List
- **Action ID:** `action_brightloop_subscription`
- **Model:** `brightloop.subscription`
- **Route / Menu:** **Subscriptions → Subscriptions → All Subscriptions**
- **Intended User:** Staff and Administrators.
- **Display Mode:** Odoo standard `<list>` view with search panel.

### B. List View Columns & Visual Decorations
- `subscription_number`: Char, unique sequence reference.
- `partner_id`: Many2one, customer name.
- `plan_id`: Many2one, subscription plan.
- `next_billing_date`: Date, next automated invoicing date.
- `amount_total`: Monetary, sum total with table column footer (`sum="Total Recurring"`).
- `is_paused`: Boolean widget `boolean_toggle`, readonly.
- `status`: Selection with badge widget.
- **Row Decorations:**
  - `decoration-muted="status == 'closed'"`
  - `decoration-info="status == 'quotation'"`
  - `decoration-warning="is_paused == True"`
  - `decoration-success="status == 'active' and is_paused == False"`

### C. Search & Filter Options
- Search fields: `subscription_number`, `partner_id`, `plan_id`.
- Quick Filters: `Draft`, `Quotations`, `Confirmed`, `Active` (Default), `Currently Paused`, `Closed`.
- Group By: `Status`, `Customer`, `Plan`.

---

## PAGE 16: Subscription Detail Form View
### A. Page Identification
- **Page ID:** PAGE 16
- **Page Name:** Subscription Management Form
- **Model:** `brightloop.subscription`
- **Display Mode:** Full Odoo `<form>` view with header workflow buttons, ribbon widgets, notebook tabs, and mail chatter.

### B. Header Workflow Action Buttons
| Button String | Method (`name`) | Context / Visibility Rule | Class | Behaviour |
|---|---|---|---|---|
| `Send Quotation` | `action_send_quotation` | `status == 'draft'` | `oe_highlight` | Moves to Quotation stage; validates minimum plan quantity |
| `Confirm Order` | `action_confirm` | `status == 'quotation'` | `oe_highlight` | Moves to Confirmed; validates quotation expiration |
| `Reset to Draft` | `action_cancel_to_draft` | `status == 'quotation'` | None | Reverts quotation to Draft for editing |
| `Activate Subscription`| `action_activate` | `status == 'confirmed'` | `oe_highlight` | Activates subscription, sets start date, anchor day, next billing |
| `Pause Subscription` | `action_pause` | `status == 'active' and not is_paused`| `btn-warning` | Pauses subscription; checks `plan.allow_pause` |
| `Resume Subscription`| `action_resume` | `status == 'active' and is_paused` | `btn-success` | Resumes subscription; recalculates billing dates by pause duration |
| `Renew Subscription` | `action_renew` | `status == 'active'` | `oe_highlight` | Extends expiry date; checks `plan.allow_renewal` |
| `Close Subscription` | `action_close` | `status in ('confirmed', 'active')` | None | Terminates subscription; checks `plan.allow_early_close` |
| **Statusbar** | `status` | Always visible | Statusbar widget | Canonical stages: `draft,quotation,confirmed,active,closed` |

### C. Sheet Layout & Form Fields
- **Ribbons:** Warning ribbon `"Paused"` (visible when `is_paused`), Danger ribbon `"Closed"` (visible when `status == 'closed'`).
- **Title:** Large heading displaying `subscription_number`.
- **Group 1: Customer & Plan:**
  - `partner_id`: Customer partner reference (readonly after confirmation).
  - `plan_id`: Subscription plan (readonly after confirmation).
  - `template_id`: Quotation template used.
  - `company_id`: Multi-company reference.
- **Group 2: Schedule & Billing:**
  - `valid_until`: Quotation validity date.
  - `start_date`: Commencement date.
  - `expiry_date`: Expiration date.
  - `next_billing_date`: Next due billing date.
  - `billing_interval`: Cadence (Daily, Weekly, Monthly, Yearly).
  - `billing_interval_count`: Cadence multiplier.
  - `renewal_count`: Count of completed renewals.
- **Group 3: Closure Details (Visible only when Closed):**
  - `closed_date`: Date closed.
  - `closure_reason`: Reason (`expired`, `user_request`, `non_payment`, `plan_ended`, `other`).
  - `early_closed`: Boolean indicating premature closure.
- **Notebook Tab 1: Subscription Lines (`line_ids`):**
  - Editable inline list: `product_id`, `variant_id`, `name`, `quantity`, `unit_price`, `discount`, `discount_id`, `tax_id`, `amount_subtotal`.
  - Subtotal & Total Monetary footer.
- **Notebook Tab 2: Commercial Terms:**
  - `payment_terms`: Commercial payment term string (`Immediate Payment`, `Net 30`, etc.).
- **Chatter:** Full Odoo mail thread, follower widget, and activity schedule mixin.

---

## PAGE 17: Customer Quotations Backend List
- **Page ID:** PAGE 17
- **Action ID:** `action_brightloop_quotations`
- **Domain Filter:** `[('status', 'in', ('draft', 'quotation'))]`
- **Context:** `{'default_status': 'draft'}`
- **Description:** Filtered view of `brightloop.subscription` dedicated to pipeline quotation management.

---

## PAGE 18: Subscription Plans List View
### A. Page Identification
- **Page ID:** PAGE 18
- **Page Name:** Subscription Plans
- **Action ID:** `action_brightloop_plan`
- **Model:** `brightloop.plan`
- **Menu:** **Catalog & Plans → Subscription Plans**

### B. List View Columns
- `name`: Plan title.
- `billing_price`: Base recurring price.
- `billing_interval`: Badge widget (Monthly in info, Yearly in success, Daily/Weekly in warning).
- `minimum_quantity`: Minimum seat/product constraint.
- `start_date`, `end_date`: Availability period.
- `allow_pause`: Boolean toggle.
- `allow_renewal`: Boolean toggle.
- `auto_close`: Boolean toggle.
- `active`: Boolean toggle.

---

## PAGE 19: Subscription Plan Form View
### A. Page Identification
- **Page ID:** PAGE 19
- **Model:** `brightloop.plan`
- **Layout:** Standard sheet with ribbon for archived state.
- **Sections:**
  - Plan Name title field.
  - Commercial Terms (`billing_price`, `billing_interval`, `billing_interval_count`, `minimum_quantity`).
  - Availability Period (`start_date`, `end_date`).
  - Plan Governance & Lifecycle Permissions (`allow_pause`, `allow_renewal`, `allow_early_close`, `auto_close`).
  - Chatter.

---

## PAGE 20: Products List View
- **Page ID:** PAGE 20
- **Action ID:** `action_brightloop_product`
- **Model:** `brightloop.product`
- **Columns:** `name`, `product_type` (badge: Software, Add-on, Service), `sales_price`, `cost_price`, `active` (boolean toggle).

---

## PAGE 21: Product Detail Form View
- **Page ID:** PAGE 21
- **Model:** `brightloop.product`
- **Fields:** Product Name, `product_type`, `sales_price`, `cost_price`, `notes`.
- **Notebook Tab 1 (Variants):** Inline sub-table `variant_ids`:
  - `name`: Variant title (e.g. "Pro Edition").
  - `price_adjustment`: Price delta (can be positive or negative).
  - `effective_price`: Readonly computed price (`sales_price + price_adjustment`).
- **Notebook Tab 2 (Notes):** Full text specifications.
- **Chatter:** Mail mixin.

---

## PAGE 22: Quotation Templates List View
- **Page ID:** PAGE 22
- **Action ID:** `action_brightloop_quotation_template`
- **Model:** `brightloop.quotation.template`
- **Columns:** `name`, `plan_id`, `validity_days`, `active`.

---

## PAGE 23: Quotation Template Form View
- **Page ID:** PAGE 23
- **Model:** `brightloop.quotation.template`
- **Fields:** Template Name, associated `plan_id`, `validity_days`.
- **Notebook Tab 1 (Offer Lines):** Sub-table of pre-configured line items: `product_id`, `variant_id`, `name`, `quantity`, `unit_price`, `tax_id`.

---

## PAGE 24: Billing Jobs Audit List View
### A. Page Identification
- **Page ID:** PAGE 24
- **Page Name:** Billing Jobs Audit
- **Action ID:** `action_brightloop_billing_job`
- **Model:** `brightloop.billing.job`
- **Menu:** **Brightloop Root → Billing Jobs**
- **Permissions:** Admin Only (`groups="brightloop_core.group_brightloop_admin"`).
- **Constraints:** `create="false"`, `delete="false"` (Strictly immutable audit ledger).

### B. List Columns & Visual Decorations
- `subscription_id`: Target subscription.
- `invoice_id`: Generated `account.move` invoice.
- `billing_period_start`, `billing_period_end`: Billing cycle dates.
- `state`: Status badge (`Pending` in warning, `Completed` in success, `Failed` in danger).
- `attempted_at`, `completed_at`: Execution audit timestamps.
- `amount_total`: Invoice total monetary sum.
- **Row Decorations:** `decoration-warning="state == 'pending'"`, `decoration-success="state == 'done'"`, `decoration-danger="state == 'failed'"`.

---

## PAGE 25: Billing Job Form View
- **Page ID:** PAGE 25
- **Model:** `brightloop.billing.job`
- **Header:** Stat button `View Invoice` (`action_view_invoice` opening generated `account.move`), statusbar widget (`pending,done,failed`).
- **Fields:** Readonly `idempotency_key`, `subscription_id`, `invoice_id`, `amount_total`, `billing_period_start`, `billing_period_end`, `attempted_at`, `completed_at`.
- **Notebook Tab (Error Details):** Displays `error_message` text trace if job failed.

---

## PAGE 26: Payments List View
### A. Page Identification
- **Page ID:** PAGE 26
- **Page Name:** Payments List
- **Action ID:** `action_brightloop_payment`
- **Model:** `brightloop.payment`
- **Menu:** **Finance → Payments**
- **Context:** Default filter `posted = 1`.

### B. Columns & Status Formatting
- `name`: Payment reference sequence (`PAY/YYYY/NNNNN`).
- `payment_date`: Receipt date.
- `partner_id`: Customer partner.
- `payment_method_id`: Configured method.
- `amount`: Total amount (Column footer sum).
- `total_allocated`: Sum allocated to invoices.
- `unallocated_amount`: Unapplied remaining funds.
- `state`: Status badge (`posted` green, `draft` yellow, `cancelled` red).
- `is_fully_allocated`, `is_overpayment`: Optional audit flags.
- **Row Decorations:**
  - `decoration-success="state == 'posted' and is_fully_allocated"`
  - `decoration-warning="state == 'posted' and not is_fully_allocated and unallocated_amount > 0"`
  - `decoration-danger="is_overpayment"`
  - `decoration-muted="state == 'cancelled'"`

---

## PAGE 27: Payment Detail Form View
### A. Page Identification
- **Page ID:** PAGE 27
- **Model:** `brightloop.payment`
- **Header:**
  - `Post Payment` button (`action_post`, visible in `draft`).
  - `Cancel` button (`action_cancel`, visible when not `cancelled`).
  - `Reset to Draft` button (`action_reset_to_draft`, visible in `cancelled`).
  - Statusbar: `draft,posted,cancelled`.
- **Alert Banner:** Warning banner `"This payment has been over-allocated. Total allocated exceeds the payment amount."` (visible when `is_overpayment == True`).
- **Form Groups:**
  - Payment Details: `partner_id`, `payment_method_id`, `amount`, `currency_id`, `payment_date`.
  - Reference & Status: `reference`, `total_allocated`, `unallocated_amount`, `is_fully_allocated`, `company_id`.
  - Notes: Text area.
- **Notebook Tab (Invoice Allocations):**
  - Sub-table `invoice_payment_ids`: `invoice_id`, `invoice_total`, `allocated_amount`, `allocation_date`, `notes`.
- **Chatter:** Mail mixin.

---

## PAGE 28: Payment Allocations List View
- **Page ID:** PAGE 28
- **Action ID:** `action_invoice_payment`
- **Model:** `brightloop.invoice.payment`
- **Menu:** **Finance → Payment Allocations**
- **Columns:** `invoice_id`, `partner_id`, `payment_id`, `invoice_total`, `allocated_amount` (sum footer), `allocation_date`.

---

## PAGE 29: Payment Allocation Form View
- **Page ID:** PAGE 29
- **Model:** `brightloop.invoice.payment`
- **Fields:** Group 1 (Invoice): `invoice_id`, `invoice_total`. Group 2 (Payment): `payment_id`, `allocated_amount`, `allocation_date`, `currency_id`. Notes field.

---

## PAGE 30: Payment Methods Configuration List View
- **Page ID:** PAGE 30
- **Action ID:** `action_payment_method`
- **Model:** `brightloop.payment.method`
- **Menu:** **Finance → Configuration → Payment Methods**
- **Permissions:** Restricted to `group_brightloop_finance_manager`.
- **View Type:** Editable bottom list view.
- **Columns:** Sequence handle, `name`, `code`, `requires_reference` (checkbox), `active` (checkbox).

---

## PAGE 31: Payment Method Form View
- **Page ID:** PAGE 31
- **Model:** `brightloop.payment.method`
- **Fields:** Method Name, `code`, `sequence`, `requires_reference`, `active`, `notes` description.

---

## PAGE 32: Staff Management List View
- **Page ID:** PAGE 32
- **Action ID:** `action_brightloop_staff_management`
- **Model:** `res.users`
- **Menu:** **Brightloop Root → Staff Management**
- **Permissions:** Admin Only (`groups="brightloop_core.group_brightloop_admin"`).
- **Domain:** `[('share', '=', False), ('groups_id', 'in', [ref('brightloop_core.group_brightloop_staff')])]`.
- **Description:** Filtered list of internal operational staff accounts.

---

## PAGE 33: Staff User Form View
- **Page ID:** PAGE 33
- **Model:** `res.users`
- **Fields:** Staff name, login email, group assignments under `Brightloop` module category (Staff vs Admin vs Finance roles).

---

# SECTION 4: MODALS & WIZARDS

---

## PAGE 34: Record Payment Wizard Modal
### A. Page Identification
- **Page ID:** PAGE 34
- **Page Name:** Record Payment Modal
- **Action ID:** `action_payment_wizard`
- **Model:** `brightloop.payment.wizard`
- **Target:** `new` (Modal Dialog).
- **Menu:** **Finance → Record Payment**

### B. Modal Layout & Interactive Behaviour
- **Header:** Title `Record a Payment`.
- **Group 1: Payment Details:**
  - `partner_id`: Customer selector. Changing customer automatically queries and populates `allocation_ids` with open invoices.
  - `payment_method_id`: Payment method selector.
  - `amount`: Payment monetary value.
  - `payment_date`: Date.
  - `reference`: Transaction reference.
- **Group 2: Invoices Allocation Sub-Table (`allocation_ids`):**
  - Columns: `invoice_number`, `due_date`, `invoice_total`, `balance_due`, `allocated_amount`.
  - Inline editing allows splitting amount across multiple open invoices.
- **Live Calculation:**
  - `total_allocated`: Dynamically computed sum of allocation rows.
  - `remaining`: Dynamically computed unallocated balance (`amount - total_allocated`).
- **Footer Buttons:**
  - `Confirm Payment` (`btn-primary`): Validates no over-allocation against balance due, creates `brightloop.payment` and `brightloop.invoice.payment` records in a single database transaction, closes modal.
  - `Cancel` (`btn-secondary`): Dismisses modal without side effects.

---

## PAGE 35: Financial Report XLSX Export Modal
### A. Page Identification
- **Page ID:** PAGE 35
- **Page Name:** Export Financial Report (XLSX)
- **Action ID:** `action_finance_export`
- **Model:** `brightloop.finance.export`
- **Target:** `new` (Modal Dialog).
- **Menu:** **Finance → Export Report** / Triggered from OWL Dashboard.

### B. States & Form Fields
1. **State 1 (`draft` - Configure):**
   - Date Range: `date_from` (default Jan 1 of current year), `date_to` (default today).
   - Filter Options: `partner_id` (optional customer filter), `subscription_id` (optional subscription filter).
   - `export_type` Selection:
     - `full_report`: Full Financial Report (All 6 sheets)
     - `payments`: Payment History
     - `invoices_all`: All Invoices
     - `invoices_outstanding`: Outstanding Invoices
     - `invoices_overdue`: Overdue Invoices
     - `revenue_summary`: Revenue Summary
     - `subscriptions`: Subscription Information
   - Footer: `Generate Report` (`btn-primary`), `Close` (`btn-secondary`).
2. **State 2 (`done` - Download):**
   - Success alert banner: `Your report is ready. Click the button below to download.`
   - Binary file download link (`file_data`) formatted as `brightloop_finance_<type>_<date>.xlsx`.
   - File name field.
   - Footer: `Close` button.

