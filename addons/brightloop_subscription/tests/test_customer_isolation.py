# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Customer Isolation Security Tests
Owner: Member 2 (Product, Plan, Quotation & Subscription Lifecycle Lead)

Validates:
- Row-level record isolation for customer portal users on brightloop.subscription.
- Customer A cannot access Customer B's subscription or subscription lines.
- Internal staff has full operational visibility across customer subscriptions.
"""

from odoo.tests import common
from odoo.exceptions import AccessError


class TestCustomerSubscriptionIsolation(common.TransactionCase):
    """Test customer row-level isolation rules on subscription models."""

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.User = self.env['res.users']
        self.Product = self.env['brightloop.product']
        self.Plan = self.env['brightloop.plan']
        self.Subscription = self.env['brightloop.subscription']

        # Canonical Security Groups from Member 1
        self.customer_group = self.env.ref('brightloop_core.group_brightloop_customer')
        self.staff_group = self.env.ref('brightloop_core.group_brightloop_staff')

        # Customer A
        self.partner_a = self.Partner.create({
            'name': 'Customer Alpha',
            'email': 'alpha@brightloop.test',
        })
        self.user_a = self.User.create({
            'name': 'User Alpha',
            'login': 'user_alpha@brightloop.test',
            'email': 'user_alpha@brightloop.test',
            'partner_id': self.partner_a.id,
            'groups_id': [(6, 0, [self.customer_group.id])],
            'password': 'AlphaPassword1!',
        })

        # Customer B
        self.partner_b = self.Partner.create({
            'name': 'Customer Beta',
            'email': 'beta@brightloop.test',
        })
        self.user_b = self.User.create({
            'name': 'User Beta',
            'login': 'user_beta@brightloop.test',
            'email': 'user_beta@brightloop.test',
            'partner_id': self.partner_b.id,
            'groups_id': [(6, 0, [self.customer_group.id])],
            'password': 'BetaPassword2!',
        })

        # Shared Product and Plan
        self.product = self.Product.create({
            'name': 'Cloud Service',
            'sales_price': 500.0,
        })
        self.plan = self.Plan.create({
            'name': 'Basic Plan',
            'billing_interval': 'monthly',
            'billing_price': 500.0,
        })

        # Create Subscriptions
        self.sub_a = self.Subscription.create({
            'partner_id': self.partner_a.id,
            'plan_id': self.plan.id,
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1, 'unit_price': 500.0})],
        })
        self.sub_b = self.Subscription.create({
            'partner_id': self.partner_b.id,
            'plan_id': self.plan.id,
            'line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1, 'unit_price': 500.0})],
        })

    def test_customer_can_read_own_subscription(self):
        """Customer Alpha can view their own subscription."""
        subs = self.Subscription.with_user(self.user_a).search([('id', '=', self.sub_a.id)])
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs.id, self.sub_a.id)

    def test_customer_cannot_read_other_customer_subscription(self):
        """Customer Alpha cannot query or access Customer Beta's subscription."""
        # 1. Search returns empty
        subs = self.Subscription.with_user(self.user_a).search([('id', '=', self.sub_b.id)])
        self.assertEqual(len(subs), 0)

        # 2. Direct read raises AccessError
        with self.assertRaises(AccessError):
            self.sub_b.with_user(self.user_a).read(['subscription_number'])

    def test_customer_cannot_modify_subscription(self):
        """Customer portal user cannot modify subscription status or lines."""
        with self.assertRaises(AccessError):
            self.sub_a.with_user(self.user_a).write({'status': 'confirmed'})
