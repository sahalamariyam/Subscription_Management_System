# Brightloop Subscription Management System — Customer Portal Specification

**Module:** `brightloop_core`  
**Workstream Lead:** Member 1 (Platform Foundation, Authentication & Security Lead)  
**Target Platform:** Odoo 18.0 Community / PostgreSQL 16 / Python 3.12  
**Implementation Phase:** Phase 4 (Customer Portal & Authentication Workflows)

---

## 1. Overview & Architecture

The Brightloop Customer Portal provides an authenticated, self-service dashboard for customers. It establishes the navigation shell and integration points for domain modules developed by the other three workstreams:
- Member 2: `brightloop_subscription` (Subscriptions & Quotations)
- Member 3: `brightloop_billing` (Recurring Invoices & Taxes)
- Member 4: `brightloop_finance` (Payments & Receipts)

All portal routes require customer authentication (`auth='user'`) and are protected by server-side record rules (`ir.rule`) ensuring strict multi-tenant isolation.

---

## 2. Customer Dashboard Layout (`/my`, `/my/home`)

Upon authentication, customers are directed to the portal home. The dashboard provides quick access cards categorized into operational domains:

```
+--------------------------------------------------------------------------+
|                       Brightloop Customer Portal                         |
+--------------------------------------------------------------------------+
|  [ My Profile ]                  |  [ Connection & Security ]            |
|  View & update contact details   |  Manage password & security settings  |
+----------------------------------+---------------------------------------+
|  [ My Subscriptions ]            |  [ My Quotations ]                    |
|  (Member 2 Integration Point)    |  (Member 2 Integration Point)         |
+----------------------------------+---------------------------------------+
|  [ My Invoices ]                 |  [ My Payments ]                      |
|  (Member 3 Integration Point)    |  (Member 4 Integration Point)         |
+--------------------------------------------------------------------------+
```

### Dashboard Entries
| Card Title | Target Route | Managing Workstream | Status |
| :--- | :--- | :--- | :--- |
| **Connection & Security** | `/my/security` | Member 1 (`brightloop_core`) | Functional (Password policy enforced) |
| **My Profile** | `/my/account` | Member 1 (`brightloop_core`) | Functional (Validated profile editing) |
| **My Subscriptions** | `/my/subscriptions` | Member 2 (`brightloop_subscription`) | Integration Placeholder |
| **My Quotations** | `/my/quotations` | Member 2 (`brightloop_subscription`) | Integration Placeholder |
| **My Invoices** | `/my/invoices` | Member 3 (`brightloop_billing`) | Integration Placeholder |
| **My Payments** | `/my/payments` | Member 4 (`brightloop_finance`) | Integration Placeholder |

---

## 3. Profile Management (`/my/account`)

Customers can view and update permitted personal and contact information.

### Permitted (Editable) Profile Fields
- `name` (Customer full name / organization name)
- `email` (Email address — validated for valid syntax and uniqueness)
- `phone` (Contact telephone)
- `street`, `street2` (Street address)
- `city`, `zipcode` (City and postal code)
- `country_id`, `state_id` (Country and State / Province)

### Strictly Protected Fields
The following fields can **never** be viewed or modified by the customer:
- `id` / `user_id` / `partner_id` (Identity identifiers)
- `groups_id` (Security group memberships)
- `share` (User classification: Internal vs. Portal)
- `parent_id` / `commercial_partner_id` (Company hierarchy)
- `signup_type` / `signup_token` (Security token attributes)
- Any financial or subscription accounting fields

### Server-Side Validation Pipeline (`details_form_validate`)
1. **Field Whitelisting:** Only fields declared in `_get_mandatory_fields()` and `_get_optional_fields()` are processed. Arbitrary submitted POST keys are rejected.
2. **Email Syntax:** Validated using RFC-compliant email regex (`^[^@\s]+@[^@\s]+\.[^@\s]+$`).
3. **Email Collision Prevention:** Verifies that the updated email is not already associated with another active user account in the system.
4. **IDOR Defense:** The controller explicitly binds updates to `request.env.user.partner_id`. Any `partner_id` or `id` passed in request bodies is discarded.

---

## 4. Multi-Tenant Customer Data Isolation

Customer isolation is enforced at the PostgreSQL query level via Odoo record rules (`ir.rule`):

### User Record Isolation (`rule_customer_res_users`)
```xml
<record id="rule_customer_res_users" model="ir.rule">
    <field name="domain_force">[('id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('brightloop_core.group_brightloop_customer'))]"/>
</record>
```
- Restricts portal customers strictly to their own user record.
- Prevents inspecting other customers or internal staff user objects.

### Partner Record Isolation (`rule_customer_res_partner`)
```xml
<record id="rule_customer_res_partner" model="ir.rule">
    <field name="domain_force">[('id', 'child_of', user.commercial_partner_id.id)]</field>
    <field name="groups" eval="[(4, ref('brightloop_core.group_brightloop_customer'))]"/>
</record>
```
- Restricts customer access to records matching `child_of` their own commercial partner.
- Permits B2B contacts within the same customer organization to view shared company contacts while preventing cross-customer data leakage.

---

## 5. Integration Contracts for Members 2, 3, and 4

When implementing your workstream addons, hook into the portal navigation using standard Odoo extension patterns:

### Member 2 (`brightloop_subscription`)
- **Route to inherit:** `/my/subscriptions` and `/my/quotations`
- **Template extension:** Extend `portal.portal_my_home` or replace placeholder template `brightloop_core.portal_integration_placeholder` for `page_name == 'subscriptions_placeholder'`.
- **Security Rule:** Add record rules on subscription models using:
  ```xml
  <field name="domain_force">[('partner_id', 'child_of', user.commercial_partner_id.id)]</field>
  <field name="groups" eval="[(4, ref('brightloop_core.group_brightloop_customer'))]"/>
  ```

### Member 3 (`brightloop_billing`)
- **Route to inherit:** `/my/invoices`
- **Security Rule:** Add record rules on invoices (`account.move`) using:
  ```xml
  <field name="domain_force">[('partner_id', 'child_of', user.commercial_partner_id.id)]</field>
  <field name="groups" eval="[(4, ref('brightloop_core.group_brightloop_customer'))]"/>
  ```

### Member 4 (`brightloop_finance`)
- **Route to inherit:** `/my/payments`
- **Security Rule:** Restrict payment transaction histories to:
  ```xml
  <field name="domain_force">[('partner_id', 'child_of', user.commercial_partner_id.id)]</field>
  <field name="groups" eval="[(4, ref('brightloop_core.group_brightloop_customer'))]"/>
  ```

---

## 6. Verification & Automated Test Coverage

The portal workflow is verified by automated HTTP integration tests in `addons/brightloop_core/tests/test_portal_http.py`:
- `test_customer_portal_dashboard_accessible`: Verifies dashboard renders with all expected integration cards.
- `test_portal_integration_placeholder_routes`: Confirms placeholder routes load cleanly with workstream attribution.
- `test_customer_profile_view_and_permitted_update`: Verifies permitted field edits update database state.
- `test_customer_profile_update_invalid_email_rejected`: Verifies email syntax enforcement on profile updates.
- `test_customer_profile_update_duplicate_email_rejected`: Verifies duplicate email collision protection.
- `test_customer_profile_idor_protection`: Verifies that passing foreign partner IDs in POST payload cannot tamper with another customer's profile.
