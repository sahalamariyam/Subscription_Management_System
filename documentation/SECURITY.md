# Brightloop Subscription Management System — Security Architecture & RBAC Specification

**Module:** `brightloop_core`  
**Workstream Lead:** Member 1 (Platform Foundation, Authentication & Security Lead)  
**Target Platform:** Odoo 18.0 Community / PostgreSQL 16 / Python 3.12  
**Security Status:** Phase 4 Hardened & Verified (Customer Portal & HTTP Authentication Workflows)

---

## 1. Overview & Security Principles

This document defines the server-side security architecture, role-based access control (RBAC), user identity conventions, and password policy for the Brightloop Subscription Management System.

All application authorization is enforced on the **server side** through Odoo's native ORM hooks, access control lists (`ir.model.access.csv`), field-level access definitions, and record rules (`ir.rule`). Frontend view modifications are treated purely as usability enhancements, never as security boundaries.

---

## 2. Canonical Security Roles & Group Hierarchy

The platform defines three canonical application-level roles under the module security category `brightloop_core.module_category_brightloop`:

| Canonical Role | Odoo Group XML ID | Implied Groups | Permission Scope |
| :--- | :--- | :--- | :--- |
| **Administrator** | `brightloop_core.group_brightloop_admin` | `brightloop_core.group_brightloop_staff` (implies `base.group_user`) | Platform administrative access: staff account creation, customer management, shared configuration, and all domain modules. **Does NOT imply `base.group_erp_manager`** (no Odoo-wide system settings access). |
| **Staff** | `brightloop_core.group_brightloop_staff` | `base.group_user` (Internal User) | Operational access: subscriptions, billing, customer support. **Cannot** create staff accounts, manage security groups, or elevate privileges. |
| **Customer** | `brightloop_core.group_brightloop_customer` | `base.group_portal` (Portal User) | External portal access: restricted strictly to own subscriptions, invoices, payments, and contact profile. |

> [!IMPORTANT]
> **Contract for Members 2, 3, and 4:**  
> Never define duplicate application roles in your modules (`brightloop_subscription`, `brightloop_billing`, `brightloop_finance`). Always reference these canonical XML IDs in your `ir.model.access.csv` and `ir.rule` definitions.

### Finding 3.2 Hardening: Least Privilege Implication
Previously, `group_brightloop_admin` implied `base.group_erp_manager`, which inadvertently granted Brightloop administrators complete control over Odoo system settings, technical parameters, and module lifecycles.  
In Phase 3.2, this implication was removed (`eval="[(6, 0, [ref('group_brightloop_staff')])]"`). Brightloop Admin now inherits only internal user rights (`base.group_user` via `group_brightloop_staff`). Model and field privileges required for staff management are granted explicitly:
- `res.users`: Explicit ACL `access_res_users_admin` with read, write, and create permissions.
- `res.partner`: `signup_type` field access granted to `group_brightloop_admin` for user invitation flows.

---

## 3. Server-Side Privilege Escalation Prevention

### Administrator Trust Model (Finding 3.1 Hardening)
The administrator privilege boundary is defined strictly by:
```python
def _is_brightloop_admin(self):
    self.ensure_one()
    return (
        self._is_superuser()
        or self.has_group('brightloop_core.group_brightloop_admin')
    )
```
- **Superuser (UID = 1):** Permitted for framework initialization, migrations, and system cron jobs.
- **Explicit Brightloop Admin Group:** Permitted for business administration.
- **ERP Managers (`base.group_erp_manager`):** Explicitly **denied** Brightloop administrative privileges unless they are also members of `brightloop_core.group_brightloop_admin`.
- **Implementation Note:** In Odoo 18, `self.env.user` returns a sudoed record (`env.su=True`). Therefore, `_is_brightloop_admin()` uses identity-based `self._is_superuser()` (`self.id == SUPERUSER_ID`) rather than `self.env.su` to prevent non-admin users from being falsely recognized as superuser in `env.user` evaluation contexts.

### Backend Enforcement Points (`models/res_users.py`)
1. **User Creation (`create`):**
   - When a non-admin calls `res.users.create()`, the system inspects `groups_id` and `share`.
   - If any privileged group (`group_brightloop_admin`, `group_brightloop_staff`, `base.group_user`, `base.group_erp_manager`, `base.group_system`) is present, or if an internal user is created (`share=False`), an `AccessError` is raised immediately.
   - Portal signups (which assign portal template groups) are safely permitted.
2. **User Modification (`write`):**
   - When a non-admin calls `res.users.write()`, modifying `groups_id` is strictly forbidden.
   - Staff members cannot promote themselves or peers to administrator.
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
   - Effect: Customers can only read and update permitted fields on their own user record (`SELF_WRITEABLE_FIELDS`). They cannot view internal staff, administrators, or other customers.
2. **Partner Model (`res.partner`):**
   - Rule ID: `brightloop_core.rule_brightloop_customer_partner_isolation`
   - Target Group: `brightloop_core.group_brightloop_customer`
   - Domain: `[('id', 'child_of', user.commercial_partner_id.id)]`
   - Effect: Customers can only view their own commercial partner record and associated child contacts. Cross-customer inspection returns empty or raises `AccessError`.

### Technical Rule Evaluation Semantics (Odoo 18)
In Odoo 18's ORM (`odoo/addons/base/models/ir_rule.py`):
1. **Global Rules (`global=True`):** Rules defined without groups apply to all users and are combined with **AND**.
2. **Group-Specific Rules (`global=False`):** All rules applying to any of the user's groups are combined with **OR**:
   ```python
   expression.AND(global_domains + [expression.OR(group_domains)])
   ```
3. **Interaction with Standard Portal Rules:**  
   Odoo's built-in portal rule on `res.partner` uses `[('id', 'child_of', user.commercial_partner_id.id)]`. Brightloop's custom rule enforces the exact same domain. Because both group rules share identical domains, `OR`-combining them yields `[('id', 'child_of', user.commercial_partner_id.id)]`, which is then `AND`-combined with the global company isolation rule. This maintains clean, predictable tenant isolation without rule conflicts.

---

## 5. Password Security Policy

### Validation Requirements
All user passwords must satisfy the following criteria:
1. **Length:** Strictly greater than 8 characters (`len(password) > 8`).
2. **Uppercase:** At least one uppercase character (`[A-Z]`).
3. **Lowercase:** At least one lowercase character (`[a-z]`).
4. **Special Character:** At least one non-alphanumeric character (`[^A-Za-z0-9]`).

### Server-Side Extension Points
* **`_validate_password_policy(password)`:** Centralized validator for cleartext passwords before hashing.
* **`_set_password()`:** Overridden on `res.users` to intercept standard password writes (`create`, `write`, `reset_password`, `signup`). Validates cleartext before hashing.
* **`_set_new_password()` (Finding 3.3 Hardening):** Overridden on `res.users` to enforce the policy immediately when `new_password` is assigned (e.g., admin resetting another user's password). Prevents policy-violating cleartext passwords from entering the ORM dirty cache prior to flush.
* **`_change_password(new_passwd)`:** Overridden to enforce policy on interactive user password changes.
* **Native Hashing Integrity:** Compliant passwords are passed to `super()._set_password()`, which hashes the password using Odoo's native Passlib `pbkdf2_sha512` CryptContext (`$pbkdf2-sha512$...`, 600,000 rounds). No plaintext passwords or reversible ciphers are stored.

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

All 58 test executions across 62 test methods in `addons/brightloop_core/tests/` pass with 0 failures and 0 errors:

### Unit & ORM Security Tests (`test_security_rbac.py`, `test_password_policy.py`, `test_shared_constants.py`)

| Test Class | Test Scenario | Status |
| :--- | :--- | :---: |
| `TestSecurityRBAC` | `test_role_computation` | **PASSED** |
| `TestSecurityRBAC` | `test_admin_creates_staff_account` | **PASSED** |
| `TestSecurityRBAC` | `test_staff_creates_staff_account_denied` | **PASSED (AccessError)** |
| `TestSecurityRBAC` | `test_customer_creates_staff_account_denied` | **PASSED (AccessError)** |
| `TestSecurityRBAC` | `test_staff_promotes_self_to_admin_denied` | **PASSED (AccessError)** |
| `TestSecurityRBAC` | `test_customer_promotes_self_to_staff_denied` | **PASSED (AccessError)** |
| `TestSecurityRBAC` | `test_unauthorized_user_assigns_privileged_groups_denied` | **PASSED (AccessError)** |
| `TestSecurityRBAC` | `test_customer_accesses_another_customer_record_denied` | **PASSED (AccessError)** |
| `TestSecurityRBAC` | `test_customer_accesses_own_permitted_record_allowed` | **PASSED** |
| `TestERPManagerBoundary` | `test_erp_manager_cannot_create_brightloop_staff` | **PASSED (AccessError)** |
| `TestERPManagerBoundary` | `test_erp_manager_cannot_assign_brightloop_privileged_groups` | **PASSED (AccessError)** |
| `TestERPManagerBoundary` | `test_erp_manager_is_not_treated_as_brightloop_admin` | **PASSED** |
| `TestERPManagerBoundary` | `test_superuser_is_treated_as_brightloop_admin` | **PASSED** |
| `TestERPManagerBoundary` | `test_brightloop_admin_can_create_staff` | **PASSED** |
| `TestERPManagerBoundary` | `test_brightloop_admin_group_does_not_imply_erp_manager` | **PASSED** |
| `TestStaffIsolation` | `test_staff_cannot_modify_another_staff_groups` | **PASSED (AccessError)** |
| `TestStaffIsolation` | `test_staff_cannot_promote_another_staff_to_admin` | **PASSED (AccessError)** |
| `TestCustomerIsolationExtended` | `test_customer_a_cannot_access_customer_b_partner` | **PASSED (AccessError)** |
| `TestCustomerIsolationExtended` | `test_customer_a_partner_not_in_search_results_for_customer_b` | **PASSED** |
| `TestCustomerIsolationExtended` | `test_customer_can_access_own_child_contact` | **PASSED** |
| `TestCustomerIsolationExtended` | `test_customer_b_cannot_access_customer_a_child_contact` | **PASSED (AccessError)** |
| `TestCustomerIsolationExtended` | `test_customer_own_permitted_profile_update_works` | **PASSED** |
| `TestPasswordPolicy` | `test_valid_password_accepted` | **PASSED** |
| `TestPasswordPolicy` | `test_password_shorter_than_required_rejected` | **PASSED (ValidationError)** |
| `TestPasswordPolicy` | `test_password_without_uppercase_rejected` | **PASSED (ValidationError)** |
| `TestPasswordPolicy` | `test_password_without_lowercase_rejected` | **PASSED (ValidationError)** |
| `TestPasswordPolicy` | `test_password_without_special_character_rejected` | **PASSED (ValidationError)** |
| `TestPasswordPolicy` | `test_password_change_supported_flow` | **PASSED** |
| `TestPasswordPolicy` | `test_native_password_authentication` | **PASSED** |
| `TestNewPasswordField` | `test_admin_writes_weak_new_password_rejected` | **PASSED (ValidationError)** |
| `TestNewPasswordField` | `test_admin_writes_valid_new_password_accepted` | **PASSED** |
| `TestNewPasswordField` | `test_admin_writes_weak_new_password_does_not_change_hash` | **PASSED** |
| `TestNewPasswordField` | `test_password_stored_as_hash_not_plaintext` | **PASSED** |
| `TestSharedConstants` | Shared status & billing interval enums | **PASSED** |

### HTTP-Level Integration Tests (`test_portal_http.py`)

| Test Class | Test Scenario | Status |
| :--- | :--- | :---: |
| `TestCustomerRegistrationHttp` | `test_public_registration_success` | **PASSED** |
| `TestCustomerRegistrationHttp` | `test_public_registration_weak_password_rejected` | **PASSED** |
| `TestCustomerRegistrationHttp` | `test_public_registration_password_mismatch_rejected` | **PASSED** |
| `TestCustomerRegistrationHttp` | `test_public_registration_invalid_email_rejected` | **PASSED** |
| `TestCustomerRegistrationHttp` | `test_public_registration_duplicate_email_rejected` | **PASSED** |
| `TestCustomerRegistrationHttp` | `test_public_registration_privilege_escalation_attempt_ignored` | **PASSED** |
| `TestPasswordResetHttp` | `test_password_reset_request_valid_email` | **PASSED** |
| `TestPasswordResetHttp` | `test_password_reset_request_anti_enumeration` | **PASSED** |
| `TestPasswordResetHttp` | `test_password_reset_request_invalid_email_syntax` | **PASSED** |
| `TestPasswordResetHttp` | `test_password_reset_with_token_weak_password_rejected` | **PASSED** |
| `TestPasswordResetHttp` | `test_password_reset_with_token_success_and_reuse_prevented` | **PASSED** |
| `TestCustomerAuthSessionHttp` | `test_customer_login_success` | **PASSED** |
| `TestCustomerAuthSessionHttp` | `test_customer_login_invalid_password` | **PASSED** |
| `TestCustomerAuthSessionHttp` | `test_customer_login_inactive_account` | **PASSED** |
| `TestCustomerAuthSessionHttp` | `test_unauthenticated_portal_access_redirects` | **PASSED** |
| `TestCustomerAuthSessionHttp` | `test_customer_logout_terminates_session` | **PASSED** |
| `TestCustomerPortalAndProfileHttp` | `test_customer_portal_dashboard_accessible` | **PASSED** |
| `TestCustomerPortalAndProfileHttp` | `test_portal_integration_placeholder_routes` | **PASSED** |
| `TestCustomerPortalAndProfileHttp` | `test_customer_profile_view_and_permitted_update` | **PASSED** |
| `TestCustomerPortalAndProfileHttp` | `test_customer_profile_update_invalid_email_rejected` | **PASSED** |
| `TestCustomerPortalAndProfileHttp` | `test_customer_profile_update_duplicate_email_rejected` | **PASSED** |
| `TestCustomerPortalAndProfileHttp` | `test_customer_profile_idor_protection` | **PASSED** |
| `TestAdminStaffManagementWorkflow` | `test_admin_staff_action_configured_correctly` | **PASSED** |
| `TestAdminStaffManagementWorkflow` | `test_menu_restricted_to_brightloop_admin` | **PASSED** |
| `TestAdminStaffManagementWorkflow` | `test_customer_cannot_access_staff_action` | **PASSED** |

---

## 8. Remaining Limitations & Production Notes

1. **Production Mail Delivery:**
   - Password reset tokens and signup invitations require an active SMTP outgoing mail server configured under **Settings → Technical → Outgoing Mail Servers**. In development/test environments, outgoing emails are recorded in `mail.mail` and verified via test mock fixtures.
2. **External Portal Profile Editing:**
   - External portal users update their profile details via the server-side validated `/my/account` controller (`details_form_validate`), which protects identity relations while permitting verified contact field updates. Direct raw ORM RPC writes from portal users remain disabled by design.
