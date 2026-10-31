# Brightloop Subscription Management System — Security Architecture & RBAC Specification

**Module:** `brightloop_core`  
**Workstream Lead:** Member 1 (Platform Foundation, Authentication & Security Lead)  
**Target Platform:** Odoo 18.0 Community / PostgreSQL 16 / Python 3.12  

---

## 1. Overview & Security Principles

This document defines the server-side security architecture, role-based access control (RBAC), user identity conventions, and password policy for the Brightloop Subscription Management System.

All application authorization is enforced on the **server side** through Odoo's native ORM hooks, access control lists (`ir.model.access.csv`), and record rules (`ir.rule`). Frontend view modifications are treated purely as usability enhancements, never as security boundaries.

---

## 2. Canonical Security Roles & XML IDs

The platform defines three canonical application-level roles under the module security category `brightloop_core.module_category_brightloop`:

| Canonical Role | Odoo Group XML ID | Implied Groups | Permission Scope |
| :--- | :--- | :--- | :--- |
| **Administrator** | `brightloop_core.group_brightloop_admin` | `brightloop_core.group_brightloop_staff`, `base.group_erp_manager` | Full platform administrative access: staff account creation, customer management, security settings, and all domain modules. |
| **Staff** | `brightloop_core.group_brightloop_staff` | `base.group_user` (Internal User) | Operational access: subscriptions, billing, customer support. **Cannot** create staff accounts, manage security groups, or elevate privileges. |
| **Customer** | `brightloop_core.group_brightloop_customer` | `base.group_portal` (Portal User) | External portal access: restricted strictly to own subscriptions, invoices, payments, and contact profile. |

> [!IMPORTANT]
> **Contract for Members 2, 3, and 4:**  
> Never define duplicate application roles in your modules (`brightloop_subscription`, `brightloop_billing`, `brightloop_finance`). Always reference these canonical XML IDs in your `ir.model.access.csv` and `ir.rule` definitions.

---

## 3. Server-Side Privilege Escalation Prevention

### Mandatory Business Rule: Admin-Only Staff Account Creation
Only an authorized Brightloop administrator (`group_brightloop_admin` or `is_admin()`) may create staff accounts or assign staff/admin security groups.

### Backend Enforcement Points (`models/res_users.py`)
1. **User Creation (`create`):**
   - When a non-admin calls `res.users.create()`, the system inspects `groups_id` and `share`.
   - If any privileged group (`group_brightloop_admin`, `group_brightloop_staff`, `base.group_user`, `base.group_erp_manager`, `base.group_system`) is present, or if an internal user is created (`share=False`), an `AccessError` is raised immediately.
   - Portal signups (which assign portal template groups) are safely permitted.
2. **User Modification (`write`):**
   - When a non-admin calls `res.users.write()`, modifying `groups_id` is strictly forbidden.
   - Staff members cannot promote themselves to administrator.
   - Customers cannot promote themselves to staff or administrator.
   - Any attempt by unauthorized users to manipulate group memberships via UI or direct RPC raises `AccessError`.

---

## 4. Customer Identity & Data Isolation

### Identity Mapping Architecture
* **Login Account (`res.users`):** Represents credentials, session state, and security group memberships.
* **Customer Profile (`res.partner`):** Represents contact info, company details, addresses, and billing profiles.
* **Association:** Standard Odoo relation where `user.partner_id` links to the customer record, and `partner.customer_user_id` / `partner.user_ids` links back.

### Row-Level Record Isolation Rules (`security/customer_rules.xml`)
1. **User Model (`res.users`):**
   - Rule ID: `brightloop_core.rule_brightloop_customer_user_isolation`
   - Target Group: `brightloop_core.group_brightloop_customer`
   - Domain: `[('id', '=', user.id)]`
   - Effect: Customers can only read their own user record. They cannot view internal staff, administrators, or other customers.
2. **Partner Model (`res.partner`):**
   - Rule ID: `brightloop_core.rule_brightloop_customer_partner_isolation`
   - Target Group: `brightloop_core.group_brightloop_customer`
   - Domain: `[('id', 'child_of', user.commercial_partner_id.id)]`
   - Effect: Customers can only view and edit their own commercial contact profile. Attempts to query or inspect other customer profiles return empty or raise `AccessError`.

---

## 5. Password Security Policy

### Validation Requirements
All user passwords must satisfy the following criteria:
1. **Length:** Strictly greater than 8 characters (`len(password) > 8`).
2. **Uppercase:** At least one uppercase character (`[A-Z]`).
3. **Lowercase:** At least one lowercase character (`[a-z]`).
4. **Special Character:** At least one non-alphanumeric character (`[^A-Za-z0-9]`).

### Server-Side Extension Points
* **`_validate_password_policy(password)`:** Validates cleartext passwords before hashing.
* **`_set_password()`:** Overridden on `res.users` to intercept all password assignment paths (`create`, `write`, `reset_password`, `signup`). If the password violates policy, a `ValidationError` is raised.
* **`_change_password(new_passwd)`:** Overridden to enforce policy on interactive user password changes.
* **Native Hashing Integrity:** Compliant passwords are passed to `super()._set_password()`, which hashes the password using Odoo's native Passlib `pbkdf2_sha512` CryptContext. No plaintext passwords or reversible ciphers (such as AES) are used.

---

## 6. Guidelines for Other Module Owners

### Member 2 (`brightloop_subscription`)
- Reference `brightloop_core.group_brightloop_customer` for portal quotation/subscription views.
- Add record rules on subscription models:
  ```xml
  <field name="domain_force">[('partner_id', 'child_of', user.commercial_partner_id.id)]</field>
  ```
- Grant `brightloop_core.group_brightloop_staff` full read/write operational access on plans and subscriptions.

### Member 3 (`brightloop_billing`)
- Reference `brightloop_core.group_brightloop_customer` for customer invoice views.
- Restrict customer invoice access using the standard partner link:
  ```xml
  <field name="domain_force">[('partner_id', 'child_of', user.commercial_partner_id.id)]</field>
  ```
- Grant `brightloop_core.group_brightloop_staff` billing operator rights.

### Member 4 (`brightloop_finance`)
- Restrict payment recording and financial dashboards to `brightloop_core.group_brightloop_staff` and `brightloop_core.group_brightloop_admin`.
- Customers must **not** have access to financial reports or revenue dashboards.

---

## 7. Automated Test Verification Matrix

All 16 automated tests in `addons/brightloop_core/tests/` passed:

| Test Scenario | Module | Status |
| :--- | :--- | :---: |
| Admin creates staff account | `test_security_rbac.py` | **PASSED** |
| Staff creates staff account | `test_security_rbac.py` | **PASSED (AccessError)** |
| Customer creates staff account | `test_security_rbac.py` | **PASSED (AccessError)** |
| Staff promotes self to admin | `test_security_rbac.py` | **PASSED (AccessError)** |
| Customer promotes self to staff | `test_security_rbac.py` | **PASSED (AccessError)** |
| Unauthorized user assigns privileged groups | `test_security_rbac.py` | **PASSED (AccessError)** |
| Customer accesses another customer record | `test_security_rbac.py` | **PASSED (Denied)** |
| Customer accesses own permitted record | `test_security_rbac.py` | **PASSED (Allowed)** |
| Valid password accepted | `test_password_policy.py` | **PASSED** |
| Password <= 8 chars rejected | `test_password_policy.py` | **PASSED (ValidationError)** |
| Password without uppercase rejected | `test_password_policy.py` | **PASSED (ValidationError)** |
| Password without lowercase rejected | `test_password_policy.py` | **PASSED (ValidationError)** |
| Password without special char rejected | `test_password_policy.py` | **PASSED (ValidationError)** |
| Password change supported flow enforced | `test_password_policy.py` | **PASSED** |
| Native password authentication works | `test_password_policy.py` | **PASSED** |
| Canonical constants integrity | `test_shared_constants.py` | **PASSED** |
