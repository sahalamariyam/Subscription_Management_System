# USER FLOWS AND JOURNEYS: BRIGHTLOOP SUBSCRIPTION MANAGEMENT SYSTEM

> **Document Type:** Senior Architectural & UI/UX Audit — Document 05 / 08  
> **Auditor Role:** Senior UI/UX Auditor, Software Architect & Frontend Reverse Engineer  
> **Project Name:** Brightloop Subscription Management System  
> **Target Downstream Consumer:** Google Stitch AI (Frontend Reconstruction & Modernization)  
> **Repository Path:** `/Users/noelsabu/Documents/subcription_management_oduu /`  
> **Audit Date:** October 31, 2026

---

## 1. Global Navigation Architecture

The Brightloop platform provides two distinct user navigation domains governed by user security groups:

```mermaid
graph TD
    User([Visitor / User]) --> AuthCheck{Authenticated?}
    
    AuthCheck -- No --> PublicRoutes[Public Navigation]
    PublicRoutes --> Login["/web/login (User Login)"]
    PublicRoutes --> Signup["/web/signup (Customer Signup)"]
    PublicRoutes --> ResetPass["/web/reset_password (Password Reset)"]
    
    AuthCheck -- Yes --> RoleCheck{User Role?}
    
    RoleCheck -- Customer (group_brightloop_customer) --> PortalDomain[Customer Portal]
    PortalDomain --> PortalHome["/my, /my/home (Portal Dashboard)"]
    PortalHome --> Profile["/my/account (Profile Editor)"]
    PortalHome --> Security["/my/security (Change Password)"]
    PortalHome --> PortalSubs["/my/subscriptions (Active Subscriptions)"]
    PortalSubs --> PortalSubDetail["/my/subscriptions/<id> (Detail)"]
    PortalHome --> PortalQuotes["/my/quotations (Commercial Quotes)"]
    PortalHome --> PortalInvoices["/my/invoices (Billing Invoices)"]
    PortalInvoices --> PortalInvDetail["/my/invoices/<id> (Detail)"]
    PortalHome --> PortalPayments["/my/payments (Payment Receipts)"]
    
    RoleCheck -- Staff / Admin --> BackendDomain[Odoo Web Client /odoo]
    BackendDomain --> AppSwitcher[Odoo Application Menu]
    
    AppSwitcher --> AppFinance[Finance App]
    AppFinance --> OWLDash[Financial Dashboard - OWL SPA]
    AppFinance --> PaymentsMenu[Payments List & Form]
    AppFinance --> AllocMenu[Payment Allocations]
    AppFinance --> ConfigMenu[Payment Methods - Admin Only]
    
    AppSwitcher --> AppSubs[Subscriptions App]
    AppSubs --> SubsMenu[All Subscriptions]
    AppSubs --> QuotesMenu[Quotations Pipeline]
    AppSubs --> CatalogMenu[Products & Variant Models]
    AppSubs --> PlansMenu[Subscription Plans]
    AppSubs --> TemplatesMenu[Quotation Templates - Admin Only]
    
    AppSwitcher --> AppPlatform[Brightloop Core - Admin Only]
    AppPlatform --> BillingJobs[Billing Jobs Audit Ledger]
    AppPlatform --> StaffMgmt[Staff Management]
```

---

## 2. Customer Registration & Onboarding Journey

```mermaid
sequenceDiagram
    autonumber
    actor Visitor as Prospective Customer
    participant UI as Browser / Frontend
    participant Server as Odoo Auth Controller
    participant DB as PostgreSQL Database

    Visitor->>UI: Navigate to /web/signup
    UI-->>Visitor: Render Registration Form (Name, Email, Passwords)
    Visitor->>UI: Fill form & click "Sign up"
    UI->>Server: POST /web/signup (name, login, password, confirm_password)
    
    Server->>Server: Validate Email Format (^[^@\s]+@[^@\s]+\.[^@\s]+$)
    Server->>DB: Check for existing login or email collision
    alt Email Collision Exists
        Server-->>UI: Display Error: "Another user is already registered..."
    else Unique Email
        Server->>Server: Execute _validate_password_policy() (len>=12, upper, lower, special)
        alt Password Weak
            Server-->>UI: Display Error: "Password must be at least 12 characters..."
        else Policy Satisfied
            Server->>DB: Create res.users & linked res.partner
            Server->>DB: Assign group_brightloop_customer (implied portal user)
            Server->>Server: Create User Session
            Server-->>UI: HTTP 302 Redirect to /my
            UI-->>Visitor: Render Customer Portal Home (/my)
        end
    end
```

---

## 3. Two-Stage Password Reset Journey (Anti-Enumeration)

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Customer / User
    participant Browser
    participant Server as Brightloop Controller
    participant DB as PostgreSQL Database
    participant Mail as Outgoing Mail Server

    Note over Customer,Mail: Stage 1: Reset Request
    Customer->>Browser: Visit /web/reset_password
    Customer->>Browser: Enter email & submit
    Browser->>Server: POST /web/reset_password (login=email)
    Server->>DB: Query res.users by login
    alt User Found & Active
        Server->>DB: Set partner.signup_type = 'reset'
        Server->>Mail: Queue reset email with cryptographic HMAC token URL
    else User Not Found
        Server->>Server: Log event internally (no visual error returned)
    end
    Server-->>Browser: Uniform Message: "If an account exists, instructions have been sent."

    Note over Customer,Mail: Stage 2: Token Redemption
    Customer->>Browser: Click link in email (/web/reset_password?token=...)
    Browser->>Server: GET /web/reset_password?token=...
    Server->>DB: Verify token HMAC signature and validity timestamp (4 hr expiry)
    Server-->>Browser: Render New Password Form
    Customer->>Browser: Submit new password & confirmation
    Browser->>Server: POST /web/reset_password (token, password, confirm_password)
    Server->>Server: Enforce strict password policy
    Server->>DB: Update password hash (PBKDF2-SHA512)
    Server->>DB: Invalidate token (signup_type = False)
    Server-->>Browser: Authenticate session & redirect to /my
```

---

## 4. Subscription Commercial Lifecycle Journey

```mermaid
stateDiagram-v2
    [*] --> Draft : Commercial rep creates quote
    
    Draft --> Quotation : action_send_quotation()
    note right of Quotation
        Enforces plan.minimum_quantity
        Computes quote expiration (valid_until)
    end note
    
    Quotation --> Draft : action_cancel_to_draft() (Revision requested)
    
    Quotation --> Confirmed : action_confirm() (Customer accepts offer)
    note right of Confirmed
        Validates quotation has not expired
    end note
    
    Confirmed --> Active : action_activate()
    note right of Active
        Sets start_date = today
        Records billing_anchor_day (e.g. 31st)
        Computes initial next_billing_date
    end note
    
    Active --> Paused : action_pause()
    note right of Paused
        Requires plan.allow_pause = True
        Preserves active status with is_paused=True
        Records pause_date
    end note
    
    Paused --> Active : action_resume()
    note right of Active
        Calculates paused duration (days)
        Shifts next_billing_date and expiry_date forward
    end note
    
    Active --> Active : action_renew()
    note right of Active
        Requires plan.allow_renewal = True
        Extends expiry_date by plan cadence
        Increments renewal_count
    end note
    
    Active --> Closed : action_close()
    Confirmed --> Closed : action_close()
    note right of Closed
        Checks plan.allow_early_close if before expiry
        Records closed_date, reason, early_closed flag
    end note
    
    Closed --> [*]
```

---

## 5. Automated Recurring Billing Engine Journey

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Daily Cron (ir.cron)
    participant Engine as brightloop.billing.engine
    participant SubModel as brightloop.subscription
    participant Lock as PostgreSQL Lock Manager
    participant MoveModel as account.move (Odoo Native)
    participant JobModel as brightloop.billing.job

    Cron->>Engine: Trigger _cron_recurring_billing() (Daily)
    Engine->>SubModel: _get_subscriptions_due_for_billing(today)
    SubModel-->>Engine: Return active, non-paused subscriptions due
    
    loop For Each Subscription Due
        Engine->>Engine: Generate deterministic idempotency_key
        Engine->>JobModel: Check existing billing job by idempotency_key
        alt Job Already Exists (Completed)
            Engine->>Engine: Skip (Duplicate Prevention)
        else Job Missing or Retrying
            Engine->>Lock: SELECT id FROM brightloop_subscription FOR UPDATE NOWAIT
            alt Lock Conflict (55P03)
                Engine->>JobModel: Log lock conflict, skip to next
            else Lock Acquired
                Engine->>JobModel: Create billing job (state='pending')
                Note over Engine,MoveModel: Isolated Savepoint Begins
                Engine->>Engine: Compute combined effective discount
                Engine->>MoveModel: Create draft invoice (move_type='out_invoice', subscription_id=sub.id)
                Engine->>SubModel: Advance next_billing_date (anchor day preserved)
                alt Processing Successful
                    Engine->>JobModel: Update job (state='done', invoice_id, completed_at)
                    Engine->>Engine: Commit savepoint
                else Processing Exception
                    Engine->>Engine: Rollback savepoint & invalidate ORM cache
                    Engine->>JobModel: Update job (state='failed', error_message)
                end
            end
        end
    end
```

---

## 6. Payment Recording & Multi-Invoice Allocation Journey

```mermaid
sequenceDiagram
    autonumber
    actor Staff as Finance User
    participant WizardUI as Payment Wizard (Modal)
    participant PaymentModel as brightloop.payment
    participant AllocModel as brightloop.invoice.payment
    participant MoveModel as account.move

    Staff->>WizardUI: Open "Record Payment" Wizard
    Staff->>WizardUI: Select Customer (partner_id)
    WizardUI->>MoveModel: Query posted customer invoices with amount_residual > 0
    MoveModel-->>WizardUI: Populate allocation sub-table with open invoices
    Staff->>WizardUI: Select Payment Method, enter Amount & Date
    Staff->>WizardUI: Distribute allocated amounts across invoice rows
    WizardUI->>WizardUI: Live calculate total_allocated & unallocated remaining
    Staff->>WizardUI: Click "Confirm Payment"
    
    WizardUI->>PaymentModel: Create brightloop.payment (state='posted')
    loop For each positive allocation line
        WizardUI->>AllocModel: Create brightloop.invoice.payment (payment_id, invoice_id, allocated_amount)
        AllocModel->>AllocModel: Validate allocated_amount <= invoice residual balance
    end
    WizardUI-->>Staff: Close Modal & Refresh Views
```

---

## 7. Financial Dashboard & XLSX Export Journey

```mermaid
sequenceDiagram
    autonumber
    actor Staff as Finance User / Manager
    participant DashboardUI as OWL 2 Component (Browser)
    participant RPC as JSON-RPC (/web/dataset/call_kw)
    participant DashModel as brightloop.finance.dashboard
    participant ExportModel as brightloop.finance.export
    participant XlsxWriter as xlsxwriter Engine

    Staff->>DashboardUI: Open Finance Dashboard
    DashboardUI->>RPC: get_dashboard_kpis(date_from, date_to)
    RPC->>DashModel: Instantiate transient record & _compute_kpis()
    DashModel->>DashModel: Aggregate allocations, residual balances, overdue counts via read_group()
    DashModel-->>RPC: Return { kpis: {...}, payments: [...] }
    RPC-->>DashboardUI: Reactive state updated; render 6 cards & collection progress bar

    Note over Staff,XlsxWriter: User Triggers Excel Export
    Staff->>DashboardUI: Click "Export to XLSX"
    DashboardUI->>RPC: export_xlsx(date_from, date_to)
    RPC->>ExportModel: Instantiate export wizard (export_type='full_report')
    ExportModel->>ExportModel: Enforce _check_report_access(partner_id)
    ExportModel->>XlsxWriter: Compile 6 formatted sheets (Payments, Invoices, Outstanding, Overdue, Revenue, Subscriptions)
    XlsxWriter-->>ExportModel: In-memory binary workbook
    ExportModel-->>RPC: Return { file_content: "<base64>", filename: "brightloop_finance_report.xlsx" }
    RPC-->>DashboardUI: Payload received
    DashboardUI->>DashboardUI: Convert Base64 -> Blob -> Create Anchor Tag -> Click Download
    DashboardUI-->>Staff: File downloaded to user's device + Success Toast displayed
```

