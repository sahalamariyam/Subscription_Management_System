# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Password Policy Automated Tests
Owner: Member 1 (Platform Foundation, Authentication & Security Lead)

Validates:
- Password policy criteria:
  - More than 8 characters (> 8)
  - At least one uppercase letter ([A-Z])
  - At least one lowercase letter ([a-z])
  - At least one special character ([^A-Za-z0-9])
- Rejection of non-compliant passwords.
- Enforcement on interactive password change.
- Odoo native password hashing and authentication integrity.
"""

from odoo.tests import common
from odoo.exceptions import ValidationError, AccessDenied


class TestPasswordPolicy(common.TransactionCase):
    """Test server-side password policy validation and native authentication."""

    def test_valid_password_accepted(self):
        """Valid complex password exceeding 8 characters is accepted."""
        user = self.env['res.users'].create({
            'name': 'Valid Password User',
            'login': 'valid_pwd_user@brightloop.test',
            'email': 'valid_pwd_user@brightloop.test',
            'password': 'SecureP@ssw0rd9',
        })
        self.assertTrue(user.exists())

    def test_password_shorter_than_required_rejected(self):
        """Passwords with 8 or fewer characters are rejected."""
        # Length 6
        with self.assertRaises(ValidationError):
            self.env['res.users'].create({
                'name': 'Short Password User',
                'login': 'short1@brightloop.test',
                'email': 'short1@brightloop.test',
                'password': 'Sh0rt!',
            })

        # Length 8 (boundary case: policy requires MORE than 8 characters)
        with self.assertRaises(ValidationError):
            self.env['res.users'].create({
                'name': 'Boundary 8 Char User',
                'login': 'eight1@brightloop.test',
                'email': 'eight1@brightloop.test',
                'password': 'Eight12!',
            })

    def test_password_without_uppercase_rejected(self):
        """Passwords without uppercase letters are rejected."""
        with self.assertRaises(ValidationError):
            self.env['res.users'].create({
                'name': 'No Upper User',
                'login': 'noupper@brightloop.test',
                'email': 'noupper@brightloop.test',
                'password': 'nouppercase123!',
            })

    def test_password_without_lowercase_rejected(self):
        """Passwords without lowercase letters are rejected."""
        with self.assertRaises(ValidationError):
            self.env['res.users'].create({
                'name': 'No Lower User',
                'login': 'nolower@brightloop.test',
                'email': 'nolower@brightloop.test',
                'password': 'NOLOWERCASE123!',
            })

    def test_password_without_special_character_rejected(self):
        """Passwords without special characters are rejected."""
        with self.assertRaises(ValidationError):
            self.env['res.users'].create({
                'name': 'No Special User',
                'login': 'nospecial@brightloop.test',
                'email': 'nospecial@brightloop.test',
                'password': 'NoSpecialChar123',
            })

    def test_password_change_supported_flow(self):
        """Password changes via change_password enforce policy."""
        initial_password = 'InitialP@ssw0rd1'
        user = self.env['res.users'].create({
            'name': 'Change Password User',
            'login': 'change_pwd_user@brightloop.test',
            'email': 'change_pwd_user@brightloop.test',
            'password': initial_password,
        })

        # 1. Non-compliant password change fails
        with self.assertRaises(ValidationError):
            user.with_user(user).change_password(initial_password, 'weakpassword')

        # 2. Compliant password change succeeds
        new_password = 'UpdatedP@ssw0rd2'
        res = user.with_user(user).change_password(initial_password, new_password)
        self.assertTrue(res)

    def test_native_password_authentication(self):
        """Odoo native authentication works with policy-validated passwords."""
        login = 'auth_user@brightloop.test'
        password = 'AuthValidP@ssw0rd1'
        user = self.env['res.users'].create({
            'name': 'Auth Test User',
            'login': login,
            'email': login,
            'password': password,
        })
        self.assertTrue(user.exists())

        # Test valid credential authentication via Odoo native verification
        credential = {'login': login, 'password': password, 'type': 'password'}
        auth_res = self.env['res.users'].with_user(user)._check_credentials(credential, {'interactive': True})
        self.assertEqual(auth_res.get('uid'), user.id)

        # Test wrong password fails with AccessDenied
        wrong_credential = {'login': login, 'password': 'WrongPassword123!', 'type': 'password'}
        with self.assertRaises(AccessDenied):
            self.env['res.users'].with_user(user)._check_credentials(wrong_credential, {'interactive': True})
