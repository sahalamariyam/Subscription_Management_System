# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Customer Portal & Auth HTTP Integration Tests
Owner: Member 1 (Platform Foundation, Authentication & Security Lead)

Covers HTTP-level integration testing for:
1. Public customer registration (/web/signup)
2. Password reset workflow & anti-enumeration (/web/reset_password)
3. Customer login, session termination & route protection
4. Customer portal dashboard, integration placeholders & profile editing
5. Staff management privilege boundaries
"""

import re
from unittest.mock import patch

import odoo
from odoo import http
from odoo.tests.common import HttpCase
from odoo.fields import Command


class TestPortalHttpBase(HttpCase):
    """Base setup for Brightloop HTTP integration tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_admin = cls.env.ref('brightloop_core.group_brightloop_admin')
        cls.group_staff = cls.env.ref('brightloop_core.group_brightloop_staff')
        cls.group_customer = cls.env.ref('brightloop_core.group_brightloop_customer')

        # Existing customer account for login & portal tests
        cls.existing_customer = cls.env['res.users'].create({
            'name': 'Existing Customer',
            'login': 'existing_cust@brightloop.test',
            'email': 'existing_cust@brightloop.test',
            'password': 'CustSecureP@ss1!',
            'groups_id': [Command.set([cls.group_customer.id])],
        })

        # Second customer account for IDOR / isolation tests
        cls.second_customer = cls.env['res.users'].create({
            'name': 'Second Customer',
            'login': 'second_cust@brightloop.test',
            'email': 'second_cust@brightloop.test',
            'password': 'CustSecureP@ss2!',
            'groups_id': [Command.set([cls.group_customer.id])],
        })

        # Staff user for privilege tests
        cls.staff_user = cls.env['res.users'].create({
            'name': 'Brightloop Staff',
            'login': 'staff_user@brightloop.test',
            'email': 'staff_user@brightloop.test',
            'password': 'StaffSecureP@ss1!',
            'groups_id': [Command.set([cls.group_staff.id])],
        })

        # Admin user
        cls.admin_user = cls.env['res.users'].create({
            'name': 'Brightloop Admin',
            'login': 'admin_user@brightloop.test',
            'email': 'admin_user@brightloop.test',
            'password': 'AdminSecureP@ss1!',
            'groups_id': [Command.set([cls.group_admin.id])],
        })

    def _get_csrf_token(self):
        """Helper to obtain a valid CSRF token for public HTTP requests."""
        self.authenticate(None, None)
        return http.Request.csrf_token(self)


class TestCustomerRegistrationHttp(TestPortalHttpBase):
    """HTTP integration tests for public customer registration (/web/signup)."""

    def test_public_registration_success(self):
        """A new customer can register with policy-compliant password and valid email."""
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'new_customer@brightloop.test',
            'name': 'New Customer User',
            'password': 'CustomerP@ssword1!',
            'confirm_password': 'CustomerP@ssword1!',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/signup', data=payload)
        self.assertIn(res.status_code, (200, 302, 303))

        # Verify user was created in DB
        user = self.env['res.users'].sudo().search([('login', '=', 'new_customer@brightloop.test')])
        self.assertTrue(user.exists(), "User should be created after successful signup")
        self.assertTrue(user.is_brightloop_customer, "New user must be assigned is_brightloop_customer")
        self.assertEqual(user.brightloop_role, 'customer', "Role must be canonical 'customer'")
        self.assertFalse(user.is_brightloop_staff, "Customer must not have staff privileges")
        self.assertFalse(user.is_brightloop_admin, "Customer must not have admin privileges")

    def test_public_registration_weak_password_rejected(self):
        """Registration with weak password (missing uppercase/special char) is rejected."""
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'weak_reg@brightloop.test',
            'name': 'Weak Reg User',
            'password': 'weakpassword',
            'confirm_password': 'weakpassword',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/signup', data=payload)
        self.assertEqual(res.status_code, 200)

        # User must not be created
        user = self.env['res.users'].sudo().search([('login', '=', 'weak_reg@brightloop.test')])
        self.assertFalse(user.exists(), "User must not be created with weak password")

    def test_public_registration_password_mismatch_rejected(self):
        """Registration with mismatched password and confirm_password is rejected."""
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'mismatch_reg@brightloop.test',
            'name': 'Mismatch Reg User',
            'password': 'ValidP@ssword1!',
            'confirm_password': 'DifferentP@ssword2!',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/signup', data=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Passwords do not match", res.text)

        user = self.env['res.users'].sudo().search([('login', '=', 'mismatch_reg@brightloop.test')])
        self.assertFalse(user.exists())

    def test_public_registration_invalid_email_rejected(self):
        """Registration with malformed email syntax is rejected."""
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'not-an-email',
            'name': 'Invalid Email User',
            'password': 'ValidP@ssword1!',
            'confirm_password': 'ValidP@ssword1!',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/signup', data=payload)
        self.assertEqual(res.status_code, 200)

        user = self.env['res.users'].sudo().search([('name', '=', 'Invalid Email User')])
        self.assertFalse(user.exists())

    def test_public_registration_duplicate_email_rejected(self):
        """Registration with an already-registered email address is rejected."""
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'existing_cust@brightloop.test',
            'name': 'Duplicate Attempter',
            'password': 'ValidP@ssword1!',
            'confirm_password': 'ValidP@ssword1!',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/signup', data=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("already registered", res.text)

    def test_public_registration_privilege_escalation_attempt_ignored(self):
        """Attempting to inject groups_id in public registration form is ignored/sanitized."""
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'hacker_reg@brightloop.test',
            'name': 'Privilege Escalation Attempter',
            'password': 'HackerP@ssword1!',
            'confirm_password': 'HackerP@ssword1!',
            'groups_id': str(self.group_admin.id),
            'share': 'False',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/signup', data=payload)
        user = self.env['res.users'].sudo().search([('login', '=', 'hacker_reg@brightloop.test')])
        if user.exists():
            self.assertFalse(user.is_brightloop_admin, "User must NOT have admin rights")
            self.assertFalse(user.is_brightloop_staff, "User must NOT have staff rights")
            self.assertEqual(user.brightloop_role, 'customer', "User must remain customer only")


class TestPasswordResetHttp(TestPortalHttpBase):
    """HTTP integration tests for password reset workflow (/web/reset_password)."""

    def test_password_reset_request_valid_email(self):
        """Submitting a registered email sends reset instructions."""
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'existing_cust@brightloop.test',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/reset_password', data=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("instructions have been sent", res.text)

    def test_password_reset_request_anti_enumeration(self):
        """Submitting an unregistered email displays generic confirmation without leaking existence."""
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'nonexistent_user@brightloop.test',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/reset_password', data=payload)
        self.assertEqual(res.status_code, 200)
        # Anti-enumeration: must NOT say "No account found"
        self.assertNotIn("No account found", res.text)
        self.assertIn("instructions have been sent", res.text)

    def test_password_reset_request_invalid_email_syntax(self):
        """Submitting an invalid email syntax shows a validation error."""
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'not_an_email_at_all',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/reset_password', data=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("valid email address", res.text)

    def test_password_reset_with_token_weak_password_rejected(self):
        """Attempting to reset password using token with weak password is rejected."""
        self.existing_customer.reset_password('existing_cust@brightloop.test')
        token = self.existing_customer.partner_id._generate_signup_token()

        csrf_token = self._get_csrf_token()
        payload = {
            'token': token,
            'password': 'weakpassword',
            'confirm_password': 'weakpassword',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/reset_password', data=payload)
        self.assertEqual(res.status_code, 200)

        # Confirm old password still works
        credential = {'login': 'existing_cust@brightloop.test', 'password': 'CustSecureP@ss1!', 'type': 'password'}
        auth_res = self.env['res.users'].with_user(self.existing_customer)._check_credentials(credential, {'interactive': True})
        self.assertEqual(auth_res.get('uid'), self.existing_customer.id)

    def test_password_reset_with_token_success_and_reuse_prevented(self):
        """
        Valid token reset:
        1. Enforces password policy on new password.
        2. Successfully updates password hash (PBKDF2-SHA512).
        3. Invalidates token so reuse is rejected.
        4. Old password fails; new password authenticates.
        """
        self.existing_customer.reset_password('existing_cust@brightloop.test')
        token = self.existing_customer.partner_id._generate_signup_token()
        new_password = 'BrandNewP@ssword9!'

        csrf_token = self._get_csrf_token()
        payload = {
            'token': token,
            'password': new_password,
            'confirm_password': new_password,
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/reset_password', data=payload)
        self.assertIn(res.status_code, (200, 302, 303))

        # Verify old password fails
        old_credential = {'login': 'existing_cust@brightloop.test', 'password': 'CustSecureP@ss1!', 'type': 'password'}
        with self.assertRaises(Exception):
            self.env['res.users'].with_user(self.existing_customer)._check_credentials(old_credential, {'interactive': True})

        # Verify new password authenticates
        new_credential = {'login': 'existing_cust@brightloop.test', 'password': new_password, 'type': 'password'}
        auth_res = self.env['res.users'].with_user(self.existing_customer)._check_credentials(new_credential, {'interactive': True})
        self.assertEqual(auth_res.get('uid'), self.existing_customer.id)

        # Attempt to reuse same token must fail
        reuse_payload = {
            'token': token,
            'password': 'AnotherNewP@ssword1!',
            'confirm_password': 'AnotherNewP@ssword1!',
            'csrf_token': self._get_csrf_token(),
        }
        reuse_res = self.url_open('/web/reset_password', data=reuse_payload)
        self.assertEqual(reuse_res.status_code, 200)
        self.assertIn("Invalid signup token", reuse_res.text)


class TestCustomerAuthSessionHttp(TestPortalHttpBase):
    """HTTP integration tests for customer login, logout, and session routing."""

    def test_customer_login_success(self):
        """Customer can authenticate through /web/login."""
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'existing_cust@brightloop.test',
            'password': 'CustSecureP@ss1!',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/login', data=payload)
        self.assertIn(res.status_code, (200, 302, 303))

    def test_customer_login_invalid_password(self):
        """Login with wrong password fails and displays error."""
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'existing_cust@brightloop.test',
            'password': 'WrongPassword123!',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/login', data=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Wrong login/password", res.text)

    def test_customer_login_inactive_account(self):
        """Login with disabled/inactive account fails."""
        inactive_user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Inactive Customer',
            'login': 'inactive_cust@brightloop.test',
            'email': 'inactive_cust@brightloop.test',
            'password': 'InactiveP@ssword1!',
            'groups_id': [Command.set([self.group_customer.id])],
        })
        inactive_user.write({'active': False})
        csrf_token = self._get_csrf_token()
        payload = {
            'login': 'inactive_cust@brightloop.test',
            'password': 'InactiveP@ssword1!',
            'csrf_token': csrf_token,
        }
        res = self.url_open('/web/login', data=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Wrong login/password", res.text)

    def test_unauthenticated_portal_access_redirects(self):
        """Accessing protected portal route /my without session redirects to /web/login."""
        self.authenticate(None, None)
        res = self.url_open('/my', allow_redirects=False)
        self.assertIn(res.status_code, (302, 303))
        self.assertIn('/web/login', res.headers.get('Location', ''))

    def test_customer_logout_terminates_session(self):
        """Logging out terminates the session and revokes access to protected portal routes."""
        self.authenticate('existing_cust@brightloop.test', 'CustSecureP@ss1!')
        portal_res = self.url_open('/my')
        self.assertEqual(portal_res.status_code, 200)

        # Log out
        self.url_open('/web/session/logout')

        # Re-check protected route
        check_res = self.url_open('/my', allow_redirects=False)
        self.assertIn(check_res.status_code, (302, 303))
        self.assertIn('/web/login', check_res.headers.get('Location', ''))


class TestCustomerPortalAndProfileHttp(TestPortalHttpBase):
    """HTTP integration tests for customer portal dashboard, profile management, and IDOR protection."""

    def test_customer_portal_dashboard_accessible(self):
        """Authenticated customer can access /my and /my/home dashboard with integration cards."""
        self.authenticate('existing_cust@brightloop.test', 'CustSecureP@ss1!')
        res = self.url_open('/my/home')
        self.assertEqual(res.status_code, 200)
        # Verify portal integration entries are present
        self.assertIn("My Subscriptions", res.text)
        self.assertIn("My Quotations", res.text)
        self.assertIn("My Invoices", res.text)
        self.assertIn("My Payments", res.text)

    def test_portal_integration_placeholder_routes(self):
        """Customer can access integration placeholders with clear workstream attribution."""
        self.authenticate('existing_cust@brightloop.test', 'CustSecureP@ss1!')

        # 1. Subscriptions placeholder (Member 2)
        res_sub = self.url_open('/my/subscriptions')
        self.assertEqual(res_sub.status_code, 200)
        self.assertIn("brightloop_subscription", res_sub.text)
        self.assertIn("Member 2", res_sub.text)

        # 2. Quotations placeholder (Member 2)
        res_quote = self.url_open('/my/quotations')
        self.assertEqual(res_quote.status_code, 200)
        self.assertIn("brightloop_subscription", res_quote.text)

        # 3. Invoices placeholder (Member 3)
        res_inv = self.url_open('/my/invoices')
        self.assertEqual(res_inv.status_code, 200)
        self.assertIn("brightloop_billing", res_inv.text)
        self.assertIn("Member 3", res_inv.text)

        # 4. Payments placeholder (Member 4)
        res_pay = self.url_open('/my/payments')
        self.assertEqual(res_pay.status_code, 200)
        self.assertIn("brightloop_finance", res_pay.text)
        self.assertIn("Member 4", res_pay.text)

    def test_customer_profile_view_and_permitted_update(self):
        """Customer can view /my/account and update permitted personal details."""
        self.authenticate('existing_cust@brightloop.test', 'CustSecureP@ss1!')
        res = self.url_open('/my/account')
        self.assertEqual(res.status_code, 200)
        self.assertIn("existing_cust@brightloop.test", res.text)

        # Perform permitted update (phone, city, street)
        csrf_token = http.Request.csrf_token(self)
        update_payload = {
            'name': 'Existing Customer Updated',
            'email': 'existing_cust@brightloop.test',
            'phone': '+15551234567',
            'street': '123 Brightloop Way',
            'city': 'San Francisco',
            'country_id': str(self.env.ref('base.us').id),
            'csrf_token': csrf_token,
        }
        post_res = self.url_open('/my/account', data=update_payload)
        self.assertIn(post_res.status_code, (200, 302, 303))

        # Verify partner was updated in database
        partner = self.existing_customer.partner_id
        self.assertEqual(partner.phone, '+15551234567')
        self.assertEqual(partner.city, 'San Francisco')

    def test_customer_profile_update_invalid_email_rejected(self):
        """Updating profile with an invalid email address is rejected."""
        self.authenticate('existing_cust@brightloop.test', 'CustSecureP@ss1!')
        csrf_token = http.Request.csrf_token(self)
        update_payload = {
            'name': 'Existing Customer',
            'email': 'invalid-email-format',
            'phone': '+15551234567',
            'street': '123 Test St',
            'city': 'San Francisco',
            'country_id': str(self.env.ref('base.us').id),
            'csrf_token': csrf_token,
        }
        res = self.url_open('/my/account', data=update_payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("valid email address", res.text)

    def test_customer_profile_update_duplicate_email_rejected(self):
        """Updating profile to an email already owned by another customer is rejected."""
        self.authenticate('existing_cust@brightloop.test', 'CustSecureP@ss1!')
        csrf_token = http.Request.csrf_token(self)
        update_payload = {
            'name': 'Existing Customer',
            'email': 'second_cust@brightloop.test',  # Belongs to second_customer
            'phone': '+15551234567',
            'street': '123 Test St',
            'city': 'San Francisco',
            'country_id': str(self.env.ref('base.us').id),
            'csrf_token': csrf_token,
        }
        res = self.url_open('/my/account', data=update_payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("already registered", res.text)

    def test_customer_profile_idor_protection(self):
        """
        IDOR Protection: /my/account strictly updates the authenticated user's partner.
        Passing another customer's partner_id in POST body or parameters has NO effect on that partner.
        """
        self.authenticate('existing_cust@brightloop.test', 'CustSecureP@ss1!')
        victim_partner = self.second_customer.partner_id
        victim_orig_phone = victim_partner.phone or ''

        csrf_token = http.Request.csrf_token(self)
        idor_payload = {
            'id': str(victim_partner.id),
            'partner_id': str(victim_partner.id),
            'name': 'Existing Customer Tamper Attempt',
            'email': 'existing_cust@brightloop.test',
            'phone': '+9999999999',
            'csrf_token': csrf_token,
        }
        self.url_open('/my/account', data=idor_payload)

        # Victim partner MUST remain completely untouched
        victim_partner.invalidate_recordset()
        self.assertEqual(victim_partner.phone or '', victim_orig_phone, "Victim partner phone must not be modified")
        self.assertEqual(victim_partner.name, 'Second Customer', "Victim partner name must not be modified")


class TestAdminStaffManagementWorkflow(TestPortalHttpBase):
    """Tests for native backend staff management workflow and privilege boundary."""

    def test_admin_staff_action_configured_correctly(self):
        """Verify the Brightloop Staff Management action is properly configured with defaults."""
        action = self.env.ref('brightloop_core.action_brightloop_staff_management')
        self.assertEqual(action.res_model, 'res.users')
        self.assertIn('group_brightloop_staff', action.context)

    def test_menu_restricted_to_brightloop_admin(self):
        """The staff management menu is strictly assigned to group_brightloop_admin."""
        menu = self.env.ref('brightloop_core.menu_brightloop_staff_management')
        self.assertIn(self.group_admin, menu.groups_id)
        self.assertNotIn(self.group_staff, menu.groups_id)
        self.assertNotIn(self.group_customer, menu.groups_id)

    def test_customer_cannot_access_staff_action(self):
        """Customer cannot read staff management action or query staff users."""
        with self.assertRaises(Exception):
            self.env['ir.actions.act_window'].with_user(self.existing_customer).browse(
                self.env.ref('brightloop_core.action_brightloop_staff_management').id
            ).check_access('read')
