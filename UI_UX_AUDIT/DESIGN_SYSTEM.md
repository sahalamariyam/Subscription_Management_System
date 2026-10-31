# DESIGN SYSTEM AUDIT & SPECIFICATION: BRIGHTLOOP SUBSCRIPTION MANAGEMENT SYSTEM

> **Document Type:** Senior Architectural & UI/UX Audit — Document 06 / 08  
> **Auditor Role:** Senior UI/UX Auditor, Software Architect & Frontend Reverse Engineer  
> **Project Name:** Brightloop Subscription Management System  
> **Target Downstream Consumer:** Google Stitch AI (Frontend Reconstruction & Modernization)  
> **Repository Path:** `/Users/noelsabu/Documents/subcription_management_oduu /`  
> **Audit Date:** October 31, 2026

---

## 1. Existing Visual Design Audit

The existing application visual design is a hybrid composed of:
1. **Odoo 18 Community Web Client:** Standard backend views using Bootstrap 5 utility classes, native form controls, and Odoo standard layout containers.
2. **Odoo Customer Portal:** Standard portal templates with basic Bootstrap 5 table styles, badge components, and minimal custom accents.
3. **Custom SCSS (`addons/brightloop_finance/static/src/dashboard.scss`):** Tailored styles for the OWL Financial Dashboard featuring custom card borders, hover elevations, and custom table headers.

---

## 2. Current Colour Palette

| Semantic Token | Exact Hex Code | CSS Variable / Class | Current Usage |
|---|---|---|---|
| **Primary Brand Blue** | `#0d6efd` / `#714B67` (Odoo) | `.text-primary`, `.btn-primary` | Primary action buttons, reference links, revenue card accent |
| **Success Green** | `#198754` | `.bg-success`, `.text-success` | Active status badges, fully allocated payment highlights, revenue metric |
| **Warning Yellow / Amber** | `#ffc107` / `#ffca2c` | `.bg-warning`, `.text-warning` | Quotation badge, outstanding balance KPI card, paused subscription ribbon |
| **Danger Red** | `#dc3545` | `.bg-danger`, `.text-danger` | Overdue invoices KPI card, closed status ribbon, failed billing jobs |
| **Info / Cyan** | `#0dcaf0` | `.bg-info`, `.text-info` | Paused subscription KPI card & portal status badge |
| **Secondary Gray** | `#6c757d` | `.bg-secondary`, `.text-muted` | Draft badges, inactive fields, column header labels |
| **Neutral Background** | `#f8f9fa` | `.bg-light`, `.bl-finance-dashboard` | Background of dashboard viewport and table headers |
| **Card Surface** | `#ffffff` | Background of `.card` | White surface for KPI metrics, forms, and tables |
| **Border Divider** | `#dee2e6` / `#e9ecef` | `.border`, `.border-bottom` | Separation borders between cards, tables, and headers |

---

## 3. Typography & Text Hierarchy

| Role | Font Family | Size | Weight | Line Height | Case / Letter Spacing |
|---|---|---|---|---|---|
| **Page Title** | System UI (`system-ui, -apple-system, sans-serif`) | `1.5rem` (24px) | 700 (Bold) | 1.2 | `-0.3px` letter spacing |
| **Large Display (KPIs)** | System UI | `1.75rem` - `2rem` (28-32px) | 700 (Bold) | 1.1 | `tabular-nums` |
| **Card / Section Header** | System UI | `1.0rem` - `1.125rem` (16-18px) | 600 (Semibold) | 1.3 | Standard |
| **KPI Sub-Label** | System UI | `0.7rem` (11.2px) | 600 (Semibold) | 1.2 | `uppercase`, `+0.2px` |
| **Table Column Headers** | System UI | `0.75rem` (12px) | 600 (Semibold) | 1.2 | `uppercase`, `+0.4px`, `#6c757d` |
| **Body & Table Cells** | System UI | `0.85rem` - `0.9rem` (13.6-14.4px)| 400 (Regular) | 1.4 | Standard |
| **Badges & Tags** | System UI | `0.75rem` (12px) | 500 (Medium) | 1.0 | Standard |

---

## 4. Component Visual Specifications

### 4.1 KPI Summary Cards (`.bl-kpi-card`)
- **Border Radius:** `12px`
- **Border:** `0` (No outer line border; flat shadow)
- **Shadow:** `0 1px 3px rgba(0, 0, 0, 0.05)`
- **Hover Transition:** `transform translateY(-2px)`, `box-shadow 0 6px 18px rgba(0,0,0,0.10)`
- **Category Accent Borders:**
  - Active Subscriptions: `border-left: 4px solid #198754`
  - Paused Subscriptions: `border-left: 4px solid #0dcaf0`
  - Revenue Received: `border-left: 4px solid #0d6efd`
  - Outstanding Balance: `border-left: 4px solid #ffc107`
  - Overdue Invoices: `border-left: 4px solid #dc3545`

### 4.2 Status Badges & Pills
- **Active Subscription:** `bg-success` (Green background, white text)
- **Paused Subscription:** `bg-info text-dark` (Cyan background, dark text)
- **Confirmed Subscription:** `bg-primary` (Blue background, white text)
- **Draft Quotation:** `bg-secondary` (Gray background, white text)
- **Sales Quotation:** `bg-warning text-dark` (Amber background, dark text)
- **Closed Subscription:** `bg-light text-muted border` (Subtle bordered pill)
- **Invoice Paid:** `bg-success`
- **Invoice Unpaid:** `bg-danger`
- **Invoice Partial:** `bg-warning text-dark`

### 4.3 Form Controls & Buttons
- **Primary Action Button:** `btn-primary`, height ~34px, border-radius `6px`, font-size `0.875rem`.
- **Secondary Action Button:** `btn-outline-secondary` / `btn-secondary`, border width `1.5px`.
- **Date Inputs:** `<input type="date">`, min-width `140px`, border-radius `6px`, padding `0.25rem 0.5rem`.
- **Table Structure:** `.table-sm`, border color `#dee2e6`, row hover highlight `#f0f4ff`.

---

## 5. Design Inconsistencies & UX Deficiencies Found

During the thorough audit of the existing screens, several visual and interaction inconsistencies were identified that Google Stitch AI must remediate:

1. **Badge Color Inconsistencies Between Views:**
   - On `/my/subscriptions`, a paused subscription renders with `.bg-info text-dark` (Cyan). On the backend list view `brightloop.subscription.tree`, paused subscriptions use `decoration-warning` (Yellow/Orange text).
   - Invoices in portal use `.badge.bg-danger` for Unpaid, while backend Odoo lists use plain default text.
2. **Visual Clutter & Form Density:**
   - In `brightloop.subscription.form`, the form header contains up to **8 action buttons** stacked horizontally, which causes button wrapping on smaller screens (tablet viewports).
3. **Table Typography & Number Alignment:**
   - In several portal tables (`/my/quotations`, `/my/subscriptions`), numerical references and monetary values lack strict tabular number font alignment (`font-variant-numeric: tabular-nums`).
4. **Empty State Inconsistencies:**
   - `/my/subscriptions` has a well-designed empty state with an icon and call-to-action button, while `/my/invoices` and `/my/payments` use plain gray text without an action button.
5. **Collection Rate Progress Bar Isolation:**
   - In the OWL dashboard, the collection rate progress bar sits in its own standalone full-width card, creating visual disconnection from the revenue metrics above it.
6. **Modal Form Padding:**
   - The Payment Wizard modal (`brightloop.payment.wizard`) displays a dense allocation table that scrolls horizontally if more than 3 open invoices are present.

---

## 6. Modernized Design System Proposal for Google Stitch AI

Google Stitch AI must reconstruct the frontend according to this modernized design token specification:

```
STITCH AI DESIGN TOKENS
├── 🎨 Modern Palette
│   ├── Primary Brand:    #4F46E5 (Indigo 600 - High Contrast & Modern)
│   ├── Primary Hover:    #4338CA (Indigo 700)
│   ├── Secondary Accent: #06B6D4 (Cyan 500)
│   ├── Success Emerald:  #10B981 (Emerald 500)
│   ├── Warning Amber:    #F59E0B (Amber 500)
│   ├── Danger Rose:      #F43F5E (Rose 500)
│   ├── Slate Dark:       #0F172A (Slate 900 - Text & Headlines)
│   ├── Slate Muted:      #64748B (Slate 500 - Secondary text & labels)
│   ├── Surface Gray:     #F8FAFC (Slate 50 - Background canvas)
│   └── Card Surface:     #FFFFFF (Pure White with subtle borders)
│
├── 📐 Spacing Scale (4px Base Grid)
│   ├── xs:  4px
│   ├── sm:  8px
│   ├── md:  16px
│   ├── lg:  24px
│   ├── xl:  32px
│   └── 2xl: 48px
│
├── 🔲 Elevation & Shadows
│   ├── Flat:    border: 1px solid #E2E8F0;
│   ├── Sm:      box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
│   ├── Md:      box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.07);
│   └── Hover:   box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
│
└── 🔤 Modern Typography Scale (Inter / SF Pro / Roboto)
    ├── Display (KPIs):  32px / 700 / letter-spacing: -0.02em / tabular-nums
    ├── H1 / Page Title: 24px / 700 / letter-spacing: -0.015em
    ├── H2 / Section:    18px / 600 / letter-spacing: -0.01em
    ├── Body Medium:     14px / 500 / line-height: 1.5
    ├── Body Regular:    14px / 400 / line-height: 1.5
    ├── Table Header:    11px / 600 / uppercase / letter-spacing: 0.05em
    └── Micro Badge:     11px / 500 / line-height: 1.0
```

