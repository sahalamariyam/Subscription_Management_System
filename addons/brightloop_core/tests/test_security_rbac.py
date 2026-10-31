# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Security & RBAC Automated Tests
Owner: Member 1 (Platform Foundation, Authentication & Security Lead)

Validates:
- Role creation and hierarchy.
- Admin-only staff account creation.
- Non-admin privilege escalation blocking.
- Customer record isolation.
- ERP Manager boundary (Finding 3.1 remediation).
- Staff cross-user isolation.
- Customer cross-customer isolation (explicit).
"""

from odoo.tests import common
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo import SUPERUSER_ID


class TestSecurityRBAC(common.TransactionCase):
    """Test Role-Based Access Control and server-side privilege boundaries."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_admin = cls.env.ref('brightloop_core.group_brightloop_admin')
        cls.group_staff = cls.env.ref('brightloop_core.group_brightloop_staff')
        cls.group_customer = cls.env.ref('brightloop_core.group_brightloop_customer')

        # 1. Platform Admin User
        cls.admin_partner = cls.env['res.partner'].create({
            'name': 'Brightloop Admin Partner',
            'email': 'admin@brightloop.test',
        })
        cls.admin_user = cls.env['res.users'].create({
            'name': 'Brightloop Admin User',
            'login': 'admin@brightloop.test',
            'email': 'admin@brightloop.test',
            'password': 'AdminSecureP@ss1',
            'partner_id': cls.admin_partner.id,
            'groups_id': [Command.set([cls.group_admin.id])],
        })

        # 2. Staff User
        cls.staff_partner = cls.env['res.partner'].create({
            'name': 'Brightloop Staff Partner',
            'email': 'staff@brightloop.test',
        })
        cls.staff_user = cls.env['res.users'].create({
            'name': 'Brightloop Staff User',
            'login': 'staff@brightloop.test',
            'email': 'staff@brightloop.test',
            'password': 'StaffSecureP@ss1',
            'partner_id': cls.staff_partner.id,
            'groups_id': [Command.set([cls.group_staff.id])],
        })

        # 3. Customer User One
        cls.customer_one_partner = cls.env['res.partner'].create({
            'name': 'Customer One Partner',
            'email': 'cust1@brightloop.test',
            'partner_share': True,
        })
        cls.customer_one = cls.env['res.users'].create({
            'name': 'Customer One User',
            'login': 'cust1@brightloop.test',
            'email': 'cust1@brightloop.test',
            'password': 'CustomerSecureP@ss1',
            'partner_id': cls.customer_one_partner.id,
            'groups_id': [Command.set([cls.group_customer.id])],
        })

        # 4. Customer User Two
        cls.customer_two_partner = cls.env['res.partner'].create({
            'name': 'Customer Two Partner',
            'email': 'cust2@brightloop.test',
            'partner_share': True,
        })
        cls.customer_two = cls.env['res.users'].create({
            'name': 'Customer Two User',
            'login': 'cust2@brightloop.test',
            'email': 'cust2@brightloop.test',
            'password': 'CustomerSecureP@ss2',
            'partner_id': cls.customer_two_partner.id,
            'groups_id': [Command.set([cls.group_customer.id])],
        })

    def test_role_computation(self):
        """Verify role fields compute properly from security groups."""
        self.assertTrue(self.admin_user.is_brightloop_admin)
        self.assertEqual(self.admin_user.brightloop_role, 'admin')

        self.assertTrue(self.staff_user.is_brightloop_staff)
        self.assertFalse(self.staff_user.is_brightloop_admin)
        self.assertEqual(self.staff_user.brightloop_role, 'staff')

        self.assertTrue(self.customer_one.is_brightloop_customer)
        self.assertFalse(self.customer_one.is_brightloop_staff)
        self.assertEqual(self.customer_one.brightloop_role, 'customer')
        self.assertTrue(self.customer_one_partner.is_brightloop_customer)

    def test_admin_creates_staff_account(self):
        """Admin is authorized to create staff accounts."""
        new_staff = self.env['res.users'].with_user(self.admin_user).create({
            'name': 'Created Staff Member',
            'login': 'created_staff@brightloop.test',
            'email': 'created_staff@brightloop.test',
            'password': 'StaffMemberP@ss1',
            'groups_id': [Command.set([self.group_staff.id])],
        })
        self.assertTrue(new_staff.exists())
        self.assertTrue(new_staff.has_group('brightloop_core.group_brightloop_staff'))

    def test_staff_creates_staff_account_denied(self):
        """Staff members are forbidden from creating staff accounts."""
        with self.assertRaises(AccessError):
            self.env['res.users'].with_user(self.staff_user).create({
                'name': 'Illegal Staff',
                'login': 'illegal_staff@brightloop.test',
                'email': 'illegal_staff@brightloop.test',
                'password': 'IllegalStaffP@ss1',
                'groups_id': [Command.set([self.group_staff.id])],
            })

    def test_customer_creates_staff_account_denied(self):
        """Customers are forbidden from creating staff accounts."""
        with self.assertRaises(AccessError):
            self.env['res.users'].with_user(self.customer_one).create({
                'name': 'Customer Created Staff',
                'login': 'cust_staff@brightloop.test',
                'email': 'cust_staff@brightloop.test',
                'password': 'CustomerStaffP@ss1',
                'groups_id': [Command.set([self.group_staff.id])],
            })

    def test_staff_promotes_self_to_admin_denied(self):
        """Staff members cannot promote themselves to administrator."""
        with self.assertRaises(AccessError):
            self.staff_user.with_user(self.staff_user).write({
                'groups_id': [Command.link(self.group_admin.id)],
            })

    def test_customer_promotes_self_to_staff_denied(self):
        """Customers cannot promote themselves to staff or admin."""
        with self.assertRaises(AccessError):
            self.customer_one.with_user(self.customer_one).write({
                'groups_id': [Command.link(self.group_staff.id)],
            })

    def test_unauthorized_user_assigns_privileged_groups_denied(self):
        """Non-admin user cannot modify security groups of other users."""
        with self.assertRaises(AccessError):
            self.customer_one.with_user(self.staff_user).write({
                'groups_id': [Command.link(self.group_staff.id)],
            })

    def test_customer_accesses_another_customer_record_denied(self):
        """Customer cannot read or search another customer's private record."""
        # 1. Partner isolation
        cust1_partner_model = self.env['res.partner'].with_user(self.customer_one)
        found_partners = cust1_partner_model.search([
            ('id', 'in', [self.customer_one_partner.id, self.customer_two_partner.id])
        ])
        self.assertIn(self.customer_one_partner.id, found_partners.ids)
        self.assertNotIn(self.customer_two_partner.id, found_partners.ids)

        with self.assertRaises(AccessError):
            cust1_partner_model.browse(self.customer_two_partner.id).check_access('read')

        # 2. User isolation
        cust1_user_model = self.env['res.users'].with_user(self.customer_one)
        found_users = cust1_user_model.search([
            ('id', 'in', [self.customer_one.id, self.customer_two.id, self.staff_user.id])
        ])
        self.assertIn(self.customer_one.id, found_users.ids)
        self.assertNotIn(self.customer_two.id, found_users.ids)
        self.assertNotIn(self.staff_user.id, found_users.ids)

        with self.assertRaises(AccessError):
            cust1_user_model.browse(self.customer_two.id).check_access('read')

    def test_customer_accesses_own_permitted_record_allowed(self):
        """Customer is allowed to read their own user and partner record."""
        cust1_partner = self.env['res.partner'].with_user(self.customer_one).browse(self.customer_one_partner.id)
        self.assertEqual(cust1_partner.id, self.customer_one_partner.id)
        self.assertEqual(cust1_partner.email, 'cust1@brightloop.test')

        cust1_user = self.env['res.users'].with_user(self.customer_one).browse(self.customer_one.id)
        self.assertEqual(cust1_user.id, self.customer_one.id)
        self.assertEqual(cust1_user.email, 'cust1@brightloop.test')


class TestERPManagerBoundary(common.TransactionCase):
    """
    Finding 3.1 remediation tests.

    Verifies that holding base.group_erp_manager WITHOUT group_brightloop_admin
    does NOT grant Brightloop administrator privileges.

    Before the fix, _is_brightloop_admin() called env.is_admin() which returns
    True for any ERP Manager.  After the fix it uses env.su (superuser only).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_admin = cls.env.ref('brightloop_core.group_brightloop_admin')
        cls.group_staff = cls.env.ref('brightloop_core.group_brightloop_staff')
        cls.group_erp_manager = cls.env.ref('base.group_erp_manager')

        # ERP Manager user — has full Odoo system rights but NO Brightloop admin group.
        cls.erp_manager_user = cls.env['res.users'].create({
            'name': 'ERP Manager Only',
            'login': 'erp_manager@brightloop.test',
            'email': 'erp_manager@brightloop.test',
            'password': 'ErpMgrSecureP@ss1',
            'groups_id': [Command.set([cls.group_erp_manager.id])],
        })

        # Brightloop Admin user — has explicit Brightloop admin group (no ERP Manager needed).
        cls.brightloop_admin_user = cls.env['res.users'].create({
            'name': 'Brightloop Admin Only',
            'login': 'bl_admin@brightloop.test',
            'email': 'bl_admin@brightloop.test',
            'password': 'BlAdminSecureP@ss1',
            'groups_id': [Command.set([cls.group_admin.id])],
        })

    def test_erp_manager_cannot_create_brightloop_staff(self):
        """
        ERP Manager without group_brightloop_admin must NOT be able to create
        a Brightloop staff account.

        This is the core Finding 3.1 regression test: if _is_brightloop_admin()
        still uses env.is_admin(), this test will FAIL (ERP Manager would be
        incorrectly granted the privilege and no AccessError would be raised).
        """
        with self.assertRaises(AccessError,
                msg="ERP Manager without Brightloop Admin must be denied staff creation"):
            self.env['res.users'].with_user(self.erp_manager_user).create({
                'name': 'Illegal Staff via ERP Manager',
                'login': 'illegal_erp_staff@brightloop.test',
                'email': 'illegal_erp_staff@brightloop.test',
                'password': 'IllegalStaffP@ss1',
                'groups_id': [Command.set([self.group_staff.id])],
            })

    def test_erp_manager_cannot_assign_brightloop_privileged_groups(self):
        """
        ERP Manager without group_brightloop_admin must NOT be able to assign
        Brightloop-privileged groups to an existing user.
        """
        target_user = self.env['res.users'].create({
            'name': 'Target User',
            'login': 'target_erp@brightloop.test',
            'email': 'target_erp@brightloop.test',
            'password': 'TargetUserP@ss1',
        })
        with self.assertRaises(AccessError,
                msg="ERP Manager must not assign Brightloop admin/staff groups"):
            target_user.with_user(self.erp_manager_user).write({
                'groups_id': [Command.link(self.group_admin.id)],
            })

    def test_erp_manager_is_not_treated_as_brightloop_admin(self):
        """
        Direct unit test of _is_brightloop_admin() method:
        ERP Manager without group_brightloop_admin must return False.

        Note: We call _is_brightloop_admin() via the superuser environment
        (to inspect the ERP manager user's record), but the METHOD itself reads
        self.env.su and self.has_group() — so we evaluate on the ERP manager
        user record using their own (non-sudo) environment to get the correct
        env.su=False result.
        """
        # with_user() sets env.user AND env.su=False (non-superuser context).
        erp_mgr_in_own_env = self.erp_manager_user.with_user(self.erp_manager_user)
        self.assertFalse(
            erp_mgr_in_own_env._is_brightloop_admin(),
            "_is_brightloop_admin() must return False for pure ERP Manager (no Brightloop Admin group)"
        )

    def test_superuser_is_treated_as_brightloop_admin(self):
        """Odoo superuser (SUPERUSER_ID = 1) must always be treated as Brightloop admin."""
        superuser = self.env['res.users'].browse(SUPERUSER_ID)
        # _is_superuser() checks self.id == SUPERUSER_ID, not env context.
        self.assertTrue(
            superuser._is_brightloop_admin(),
            "Superuser (UID=1) must always pass _is_brightloop_admin()"
        )

    def test_brightloop_admin_can_create_staff(self):
        """Explicit Brightloop Admin (no ERP Manager group) can create staff accounts."""
        new_staff = self.env['res.users'].with_user(self.brightloop_admin_user).create({
            'name': 'Staff Created By BL Admin',
            'login': 'staff_by_bl_admin@brightloop.test',
            'email': 'staff_by_bl_admin@brightloop.test',
            'password': 'StaffByBLAdminP@ss1',
            'groups_id': [Command.set([self.group_staff.id])],
        })
        self.assertTrue(new_staff.exists())
        self.assertTrue(new_staff.has_group('brightloop_core.group_brightloop_staff'))

    def test_brightloop_admin_group_does_not_imply_erp_manager(self):
        """
        Finding 3.2 remediation test.

        group_brightloop_admin must NOT imply base.group_erp_manager after the fix.
        The admin group should only imply group_brightloop_staff → base.group_user.
        """
        self.assertFalse(
            self.brightloop_admin_user.has_group('base.group_erp_manager'),
            "group_brightloop_admin must not imply base.group_erp_manager after Finding 3.2 fix"
        )
        # Admin should still be an internal user (via staff → base.group_user).
        self.assertTrue(
            self.brightloop_admin_user.has_group('base.group_user'),
            "group_brightloop_admin must still imply base.group_user (via staff)"
        )


class TestStaffIsolation(common.TransactionCase):
    """
    Finding 3.4 coverage — staff cross-user isolation.

    Verifies that a staff member cannot read or modify another staff member's
    sensitive user information via the Brightloop security framework.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_staff = cls.env.ref('brightloop_core.group_brightloop_staff')

        cls.staff_one = cls.env['res.users'].create({
            'name': 'Staff One',
            'login': 'staffone@brightloop.test',
            'email': 'staffone@brightloop.test',
            'password': 'StaffOneP@ssword1!',
            'groups_id': [Command.set([cls.group_staff.id])],
        })
        cls.staff_two = cls.env['res.users'].create({
            'name': 'Staff Two',
            'login': 'stafftwo@brightloop.test',
            'email': 'stafftwo@brightloop.test',
            'password': 'StaffTwoP@ssword1!',
            'groups_id': [Command.set([cls.group_staff.id])],
        })

    def test_staff_cannot_modify_another_staff_groups(self):
        """Staff member cannot assign privileged groups to another staff member."""
        group_admin = self.env.ref('brightloop_core.group_brightloop_admin')
        with self.assertRaises(AccessError,
                msg="Staff must not be able to assign Brightloop Admin group to another user"):
            self.staff_two.with_user(self.staff_one).write({
                'groups_id': [Command.link(group_admin.id)],
            })

    def test_staff_cannot_promote_another_staff_to_admin(self):
        """Staff cannot promote a peer to Brightloop Admin via groups_id write."""
        group_admin = self.env.ref('brightloop_core.group_brightloop_admin')
        with self.assertRaises(AccessError):
            self.staff_two.with_user(self.staff_one).write({
                'groups_id': [Command.set([group_admin.id])],
            })


class TestCustomerIsolationExtended(common.TransactionCase):
    """
    Finding 3.4 coverage — explicit customer cross-isolation tests.

    Supplements the existing test in TestSecurityRBAC with additional
    explicit isolation scenarios.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_customer = cls.env.ref('brightloop_core.group_brightloop_customer')

        cls.partner_a = cls.env['res.partner'].create({
            'name': 'Customer A Company',
            'email': 'customer_a@brightloop.test',
            'is_company': True,
            'partner_share': True,
        })
        cls.customer_a = cls.env['res.users'].create({
            'name': 'Customer A User',
            'login': 'customer_a@brightloop.test',
            'email': 'customer_a@brightloop.test',
            'password': 'CustomerASecureP@ss1',
            'partner_id': cls.partner_a.id,
            'groups_id': [Command.set([cls.group_customer.id])],
        })

        cls.partner_b = cls.env['res.partner'].create({
            'name': 'Customer B Company',
            'email': 'customer_b@brightloop.test',
            'is_company': True,
            'partner_share': True,
        })
        cls.customer_b = cls.env['res.users'].create({
            'name': 'Customer B User',
            'login': 'customer_b@brightloop.test',
            'email': 'customer_b@brightloop.test',
            'password': 'CustomerBSecureP@ss2',
            'partner_id': cls.partner_b.id,
            'groups_id': [Command.set([cls.group_customer.id])],
        })

        # Child contact of Customer A (same commercial_partner_id = partner_a)
        cls.partner_a_child = cls.env['res.partner'].create({
            'name': 'Customer A Child Contact',
            'email': 'child_a@brightloop.test',
            'parent_id': cls.partner_a.id,
        })

    def test_customer_a_cannot_access_customer_b_partner(self):
        """Customer A must not be able to read Customer B's partner record."""
        with self.assertRaises(AccessError,
                msg="Customer A must not access Customer B's partner via check_access"):
            self.env['res.partner'].with_user(self.customer_a)\
                .browse(self.partner_b.id).check_access('read')

    def test_customer_a_partner_not_in_search_results_for_customer_b(self):
        """Customer B's partner must not appear in Customer A's search results."""
        results = self.env['res.partner'].with_user(self.customer_a).search([
            ('id', 'in', [self.partner_a.id, self.partner_b.id])
        ])
        self.assertIn(self.partner_a.id, results.ids,
            "Customer A should see their own partner")
        self.assertNotIn(self.partner_b.id, results.ids,
            "Customer A must not see Customer B's partner in search")

    def test_customer_can_access_own_child_contact(self):
        """
        Customer A (company) can access their own child contact partner.

        This is the intentional 'child_of' design choice documented in the
        security audit.  The rule domain [('id', 'child_of', commercial_partner_id)]
        allows a company customer to see their own contact sub-records.
        """
        results = self.env['res.partner'].with_user(self.customer_a).search([
            ('id', '=', self.partner_a_child.id)
        ])
        self.assertIn(self.partner_a_child.id, results.ids,
            "Customer A must be able to see their own child contacts (child_of design)")

    def test_customer_b_cannot_access_customer_a_child_contact(self):
        """Customer B must not be able to access Customer A's child contacts."""
        with self.assertRaises(AccessError,
                msg="Customer B must not access Customer A's child contact"):
            self.env['res.partner'].with_user(self.customer_b)\
                .browse(self.partner_a_child.id).check_access('read')

    def test_customer_own_permitted_profile_update_works(self):
        """
        Customer can update their own permitted user profile fields (name, email)
        via self-writeable fields on res.users, but cannot update another user's profile.
        """
        # 1. Customer can update their own user profile (whitelisted in SELF_WRITEABLE_FIELDS)
        self.customer_a.with_user(self.customer_a).write({
            'name': 'Customer A Updated Name',
        })
        self.assertEqual(self.customer_a.name, 'Customer A Updated Name')

        # 2. Customer cannot update another customer's user profile
        with self.assertRaises(AccessError,
                msg="Customer A must not be able to update Customer B's profile"):
            self.customer_b.with_user(self.customer_a).write({
                'name': 'Malicious Name Tampering',
            })

