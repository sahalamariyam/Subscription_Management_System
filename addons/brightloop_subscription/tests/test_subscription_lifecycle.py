# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Subscription Lifecycle Unit Tests
Owner: Member 2 (Product, Plan, Quotation & Subscription Lifecycle Lead)

Validates:
- Unique sequence numbering (SUB/YYYY/NNNNN).
- Exact canonical lifecycle: Draft -> Quotation -> Confirmed -> Active -> Closed.
- Rejection of invalid lifecycle transitions.
- Start and expiry date consistency.
- Pause permission enforcement and date adjustment upon resume.
- Renewal permission enforcement and renewal count tracking.
- Early closure permission enforcement.
- Automated closure engine.
- Cross-module integration interface for Member 3 (advance next_billing_date).
"""

from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests import common
from odoo.exceptions import ValidationError, UserError
from odoo.addons.brightloop_core.models.shared_constants import (
    SUBSCRIPTION_STATUS_DRAFT,
    SUBSCRIPTION_STATUS_QUOTATION,
    SUBSCRIPTION_STATUS_CONFIRMED,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_CLOSED,
)


class TestBrightloopSubscriptionLifecycle(common.TransactionCase):
    """Test subscription sequence, state machine transitions, and governance rules."""

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.Product = self.env['brightloop.product']
        self.Plan = self.env['brightloop.plan']
        self.Subscription = self.env['brightloop.subscription']

        self.customer = self.Partner.create({
            'name': 'Brightloop Client Ltd',
            'email': 'billing@client.test',
        })

        self.product = self.Product.create({
            'name': 'Cloud Suite Pro',
            'product_type': 'software',
            'sales_price': 1000.0,
        })

        self.plan = self.Plan.create({
            'name': 'Standard Monthly Plan',
            'billing_interval': 'monthly',
            'billing_price': 1000.0,
            'minimum_quantity': 1,
            'allow_pause': True,
            'allow_renewal': True,
            'allow_early_close': True,
            'auto_close': False,
        })

    def _create_standard_subscription(self, plan=None):
        target_plan = plan or self.plan
        return self.Subscription.create({
            'partner_id': self.customer.id,
            'plan_id': target_plan.id,
            'status': SUBSCRIPTION_STATUS_DRAFT,
            'line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'quantity': 1.0,
                    'unit_price': 1000.0,
                    'tax_id': 'GST_18',
                })
            ]
        })

    def test_unique_subscription_number_generation(self):
        """Subscriptions receive unique sequential identifiers."""
        sub1 = self._create_standard_subscription()
        sub2 = self._create_standard_subscription()
        self.assertTrue(sub1.subscription_number.startswith('SUB/'))
        self.assertTrue(sub2.subscription_number.startswith('SUB/'))
        self.assertNotEqual(sub1.subscription_number, sub2.subscription_number)

    def test_customer_id_alias_compatibility(self):
        """customer_id alias points directly to partner_id for Member 4 compatibility."""
        sub = self._create_standard_subscription()
        self.assertEqual(sub.customer_id, self.customer)
        self.assertEqual(sub.partner_id, self.customer)

    def test_full_canonical_lifecycle(self):
        """Test complete progression: Draft -> Quotation -> Confirmed -> Active -> Closed."""
        sub = self._create_standard_subscription()
        self.assertEqual(sub.status, SUBSCRIPTION_STATUS_DRAFT)

        # 1. Draft -> Quotation
        sub.action_send_quotation()
        self.assertEqual(sub.status, SUBSCRIPTION_STATUS_QUOTATION)

        # 2. Quotation -> Confirmed
        sub.action_confirm()
        self.assertEqual(sub.status, SUBSCRIPTION_STATUS_CONFIRMED)

        # 3. Confirmed -> Active
        sub.action_activate()
        self.assertEqual(sub.status, SUBSCRIPTION_STATUS_ACTIVE)
        self.assertTrue(sub.start_date)
        self.assertTrue(sub.next_billing_date)
        # For monthly plan, next_billing_date should be 1 month ahead
        self.assertEqual(sub.next_billing_date, sub.start_date + relativedelta(months=1))

        # 4. Active -> Closed
        sub.action_close(reason='user_request')
        self.assertEqual(sub.status, SUBSCRIPTION_STATUS_CLOSED)
        self.assertTrue(sub.closed_date)
        self.assertEqual(sub.closure_reason, 'user_request')

    def test_invalid_state_transitions_rejected(self):
        """Cannot activate directly from Draft or Quotation."""
        sub = self._create_standard_subscription()
        with self.assertRaises(UserError):
            sub.action_activate()

        sub.action_send_quotation()
        with self.assertRaises(UserError):
            sub.action_activate()

    def test_pause_permission_enforced(self):
        """Pausing is rejected if the plan does not permit it."""
        no_pause_plan = self.Plan.create({
            'name': 'Strict No Pause Plan',
            'billing_interval': 'monthly',
            'billing_price': 1000.0,
            'allow_pause': False,
        })
        sub = self._create_standard_subscription(plan=no_pause_plan)
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_activate()

        with self.assertRaises(UserError):
            sub.action_pause()

    def test_pause_and_resume_workflow(self):
        """Pausing sets flag; resuming shifts next billing date and expiry date."""
        sub = self._create_standard_subscription()
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_activate()

        initial_billing_date = sub.next_billing_date
        initial_expiry_date = sub.expiry_date

        sub.action_pause()
        self.assertTrue(sub.is_paused)
        self.assertEqual(sub.status, SUBSCRIPTION_STATUS_ACTIVE)  # Retains canonical active status

        # Simulate 10 days of pause
        sub.pause_date = date.today() - relativedelta(days=10)
        sub.action_resume()

        self.assertFalse(sub.is_paused)
        self.assertEqual(sub.next_billing_date, initial_billing_date + relativedelta(days=10))
        self.assertEqual(sub.expiry_date, initial_expiry_date + relativedelta(days=10))

    def test_renewal_permission_and_counter(self):
        """Renewal increments counter and advances expiry date."""
        sub = self._create_standard_subscription()
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_activate()

        initial_expiry = sub.expiry_date
        self.assertEqual(sub.renewal_count, 0)

        sub.action_renew()
        self.assertEqual(sub.renewal_count, 1)
        self.assertEqual(sub.expiry_date, initial_expiry + relativedelta(months=1))

    def test_renewal_rejected_when_forbidden_by_plan(self):
        """Plan with allow_renewal=False rejects renewal action."""
        no_renew_plan = self.Plan.create({
            'name': 'One-off Contract',
            'billing_interval': 'monthly',
            'billing_price': 500.0,
            'allow_renewal': False,
        })
        sub = self._create_standard_subscription(plan=no_renew_plan)
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_activate()

        with self.assertRaises(UserError):
            sub.action_renew()

    def test_early_closure_permission_enforced(self):
        """Closing early when plan does not permit it raises UserError."""
        strict_plan = self.Plan.create({
            'name': 'Fixed 1-Year Lockin Plan',
            'billing_interval': 'yearly',
            'billing_price': 12000.0,
            'allow_early_close': False,
        })
        sub = self._create_standard_subscription(plan=strict_plan)
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_activate()
        sub.expiry_date = date.today() + relativedelta(months=6)

        with self.assertRaises(UserError):
            sub.action_close(reason='user_request')

    def test_member_3_billing_advancement_interface(self):
        """Member 3 can trigger next_billing_date advancement after generating invoice."""
        sub = self._create_standard_subscription()
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_activate()

        current_next_billing = sub.next_billing_date
        sub.action_advance_billing_date()
        expected_next_billing = sub.plan_id.compute_next_billing_date(
            current_next_billing,
            anchor_day=sub.billing_anchor_day,
        )
        self.assertEqual(sub.next_billing_date, expected_next_billing)

    def test_automatic_closure_cron(self):
        """Cron automatically closes expired subscriptions under auto_close plans."""
        auto_close_plan = self.Plan.create({
            'name': 'Auto-Terminating Plan',
            'billing_interval': 'monthly',
            'billing_price': 500.0,
            'auto_close': True,
        })
        sub = self._create_standard_subscription(plan=auto_close_plan)
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_activate()

        # Simulate expiry date reached yesterday
        sub.write({
            'start_date': date.today() - relativedelta(days=30),
            'expiry_date': date.today() - relativedelta(days=1),
        })

        self.Subscription._cron_auto_close_subscriptions()
        self.assertEqual(sub.status, SUBSCRIPTION_STATUS_CLOSED)
        self.assertEqual(sub.closure_reason, 'expired')

    def test_member_3_get_subscriptions_due_for_billing(self):
        """Member 3 can query due active subscriptions via _get_subscriptions_due_for_billing."""
        sub = self._create_standard_subscription()
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_activate()

        # Target date matching next billing date
        due_subs = self.Subscription._get_subscriptions_due_for_billing(sub.next_billing_date)
        self.assertIn(sub, due_subs)

        # Before next billing date should not include it
        before_date = sub.next_billing_date - relativedelta(days=5)
        early_subs = self.Subscription._get_subscriptions_due_for_billing(before_date)
        self.assertNotIn(sub, early_subs)

        # Paused subscription should not be returned for billing
        sub.action_pause()
        paused_due_subs = self.Subscription._get_subscriptions_due_for_billing(sub.next_billing_date)
        self.assertNotIn(sub, paused_due_subs)

    def test_member_3_state_and_company_fields(self):
        """Verify state alias and company_id exist on subscription."""
        sub = self._create_standard_subscription()
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_activate()

        self.assertEqual(sub.state, SUBSCRIPTION_STATUS_ACTIVE)
        self.assertEqual(sub.state, sub.status)
        self.assertTrue(sub.company_id)
        self.assertEqual(sub.billing_interval, 'monthly')
        self.assertEqual(sub.billing_interval_count, 1)

    def test_subscription_line_discounts_and_anchor_day(self):
        """Verify discount percentage, discount amount, and anchor day."""
        sub = self.Subscription.create({
            'partner_id': self.customer.id,
            'plan_id': self.plan.id,
            'status': SUBSCRIPTION_STATUS_DRAFT,
            'line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'quantity': 2.0,
                    'unit_price': 1000.0,
                    'discount': 10.0,  # 10% discount
                    'discount_amount': 50.0,  # 50 flat discount
                    'discount_id': 'DISC_SUMMER_10',
                    'tax_id': 'GST_18',
                })
            ]
        })
        line = sub.line_ids[0]
        # subtotal: (2 * 1000) * 0.9 - 50 = 1800 - 50 = 1750.0
        self.assertEqual(line.amount_subtotal, 1750.0)

        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_activate()

        # Anchor day recorded
        self.assertEqual(sub.billing_anchor_day, sub.start_date.day)

        # Advance billing date via Member 3 callback
        old_billing_date = sub.next_billing_date
        sub._update_next_billing_date()
        expected_date = sub.plan_id.compute_next_billing_date(
            old_billing_date,
            anchor_day=sub.billing_anchor_day,
        )
        self.assertEqual(sub.next_billing_date, expected_date)
