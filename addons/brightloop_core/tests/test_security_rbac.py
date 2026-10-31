# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Security & RBAC Automated Tests
Owner: Member 1 (Platform Foundation, Authentication & Security Lead)

Validates:
- Role creation and hierarchy.
- Admin-only staff account creation.
- Non-admin privilege escalation blocking.
- Customer record isolation.
"""

from odoo.tests import common
from odoo.exceptions import AccessError
from odoo.fields import Command


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
