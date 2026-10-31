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
- new_password field policy enforcement (Finding 3.3 remediation).
"""

from odoo.tests import common
from odoo.exceptions import ValidationError, AccessDenied
from odoo.fields import Command


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


class TestNewPasswordField(common.TransactionCase):
    """
    Finding 3.3 remediation tests.

    Verifies that the new_password field (used by admins to set another user's
    password) enforces the Brightloop password policy immediately (before the
    value reaches the ORM dirty cache), not only at flush time.

    The Odoo 18 base _set_new_password() assigns user.password = user.new_password
    without any validation.  Our override calls _validate_password_policy() before
    delegating to super(), so a weak value raises ValidationError immediately.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_admin = cls.env.ref('brightloop_core.group_brightloop_admin')

        cls.admin_user = cls.env['res.users'].create({
            'name': 'Password Admin',
            'login': 'pwd_admin@brightloop.test',
            'email': 'pwd_admin@brightloop.test',
            'password': 'AdminPwdSecureP@ss1',
            'groups_id': [Command.set([cls.group_admin.id])],
        })

        cls.target_user = cls.env['res.users'].create({
            'name': 'Password Target',
            'login': 'pwd_target@brightloop.test',
            'email': 'pwd_target@brightloop.test',
            'password': 'TargetInitialP@ss1',
        })

    def test_admin_writes_weak_new_password_rejected(self):
        """
        Admin writing a weak password via new_password field must be rejected.

        This is the primary Finding 3.3 regression test.  Before the fix,
        write({'new_password': 'weak'}) would pass the write() call and only
        raise at flush time (if the flush exception was caught, the weak value
        could linger in the ORM cache).  After the fix, _set_new_password()
        validates immediately.
        """
        with self.assertRaises(ValidationError,
                msg="Weak new_password must be rejected with ValidationError"):
            self.target_user.with_user(self.admin_user).write({
                'new_password': 'weakpass',
            })
            # Explicit flush to trigger the inverse — ensures the check fires
            # even if the ORM buffers the write.
            self.env.flush_all()

    def test_admin_writes_valid_new_password_accepted(self):
        """
        Admin writing a policy-compliant password via new_password field must succeed
        without raising any exception.

        We verify the write does not raise; we do NOT re-authenticate because
        _check_credentials() reads from self.env.user (the session user) and
        password hashing via new_password requires a flush that may not propagate
        cleanly in a TransactionCase test isolation context.  Full authentication
        after new_password is covered by test_native_password_authentication
        which uses the password field directly.
        """
        new_pwd = 'ValidNewP@ssword9!'
        # Must not raise — this is the primary assertion.
        self.target_user.with_user(self.admin_user).write({
            'new_password': new_pwd,
        })
        self.env.flush_all()
        # Verify the user record still exists (no unrecoverable ORM state).
        self.assertTrue(self.target_user.exists(),
            "Target user must still exist after valid new_password write")

    def test_admin_writes_weak_new_password_does_not_change_hash(self):
        """
        After a rejected weak new_password write, the user's password hash
        in the DB must remain unchanged (the original hash must still be valid).
        """
        # Record the current hash before attempting the rejected write.
        self.env.cr.execute(
            "SELECT password FROM res_users WHERE id = %s", (self.target_user.id,)
        )
        original_hash = self.env.cr.fetchone()[0]

        # Attempt (should raise ValidationError from our _set_new_password override).
        with self.assertRaises(ValidationError,
                msg="Weak new_password must be rejected"):
            self.target_user.with_user(self.admin_user).write({
                'new_password': 'tooweak',
            })
            self.env.flush_all()

        # Hash must be unchanged.
        self.env.cr.execute(
            "SELECT password FROM res_users WHERE id = %s", (self.target_user.id,)
        )
        current_hash = self.env.cr.fetchone()[0]
        self.assertEqual(original_hash, current_hash,
            "Password hash must be unchanged after a rejected new_password write")

    def test_password_stored_as_hash_not_plaintext(self):
        """
        After any password set operation, the stored value in res_users.password
        must be a Passlib hash (not the original plaintext string).
        """
        pwd = 'HashCheckP@ssword9!'
        user = self.env['res.users'].create({
            'name': 'Hash Check User',
            'login': 'hashcheck@brightloop.test',
            'email': 'hashcheck@brightloop.test',
            'password': pwd,
        })
        # Read the raw stored password directly via SQL.
        self.env.cr.execute(
            "SELECT password FROM res_users WHERE id = %s", (user.id,)
        )
        row = self.env.cr.fetchone()
        self.assertIsNotNone(row, "User must exist in DB")
        stored_pw = row[0]
        self.assertNotEqual(stored_pw, pwd,
            "Stored password must not be the plaintext value")
        # Passlib PBKDF2-SHA512 hashes start with '$pbkdf2-sha512$'
        self.assertTrue(
            stored_pw and stored_pw.startswith('$'),
            f"Stored value must be a Passlib hash (starts with '$'), got: {stored_pw!r}"
        )

    # -----------------------------------------------------------------------
    # Documented limitations — HTTP-context flows
    # -----------------------------------------------------------------------
    # The following flows CANNOT be covered by TransactionCase unit tests
    # because they require an active HTTP request context:
    #
    #   1. Token-based password reset (_reset_password / web controller)
    #      - Generates a one-time token via email and processes it over HTTP.
    #      - Requires odoo.tests.HttpCase or a mocked request environment.
    #
    #   2. Portal signup flow (auth_signup module)
    #      - Processes the public /web/signup route.
    #      - Requires HttpCase.
    #
    # These paths ultimately call _change_password() or write({'password': ...}),
    # both of which ARE covered by existing unit tests.  The HTTP integration
    # tests are deferred to Phase 4 (Customer Portal) when HttpCase scaffolding
    # will be available.  They are recorded here so the coverage gap is visible.
    # -----------------------------------------------------------------------
