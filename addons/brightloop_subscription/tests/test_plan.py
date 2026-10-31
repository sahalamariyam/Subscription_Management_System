# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Plan Unit Tests
Owner: Member 2 (Product, Plan, Quotation & Subscription Lifecycle Lead)

Validates:
- All four billing intervals (daily, weekly, monthly, yearly).
- Next billing date computation per interval.
- Minimum quantity validation (>= 1).
- Non-negative billing price validation.
- Invalid availability dates (end_date < start_date).
- Governance permission flags: auto_close, allow_early_close, allow_pause, allow_renewal.
"""

from datetime import date
from odoo.tests import common
from odoo.exceptions import ValidationError
from odoo.addons.brightloop_core.models.shared_constants import (
    BILLING_INTERVAL_DAILY,
    BILLING_INTERVAL_WEEKLY,
    BILLING_INTERVAL_MONTHLY,
    BILLING_INTERVAL_YEARLY,
)


class TestBrightloopPlan(common.TransactionCase):
    """Test subscription plan creation, interval computation, and validation."""

    def setUp(self):
        super().setUp()
        self.Plan = self.env['brightloop.plan']

    def test_plan_all_four_billing_intervals(self):
        """Plans support daily, weekly, monthly, and yearly intervals."""
        intervals = [
            (BILLING_INTERVAL_DAILY, 'Daily SaaS Plan'),
            (BILLING_INTERVAL_WEEKLY, 'Weekly Trial Plan'),
            (BILLING_INTERVAL_MONTHLY, 'Monthly Standard Plan'),
            (BILLING_INTERVAL_YEARLY, 'Annual Enterprise Plan'),
        ]
        for interval_code, plan_name in intervals:
            plan = self.Plan.create({
                'name': plan_name,
                'billing_price': 100.0,
                'billing_interval': interval_code,
                'minimum_quantity': 1,
            })
            self.assertEqual(plan.billing_interval, interval_code)

    def test_next_billing_date_computation(self):
        """Verify date progression logic for each interval."""
        base_date = date(2026, 1, 15)

        daily_plan = self.Plan.create({
            'name': 'Daily Plan',
            'billing_interval': BILLING_INTERVAL_DAILY,
            'billing_price': 50.0,
        })
        self.assertEqual(daily_plan.compute_next_billing_date(base_date), date(2026, 1, 16))

        weekly_plan = self.Plan.create({
            'name': 'Weekly Plan',
            'billing_interval': BILLING_INTERVAL_WEEKLY,
            'billing_price': 200.0,
        })
        self.assertEqual(weekly_plan.compute_next_billing_date(base_date), date(2026, 1, 22))

        monthly_plan = self.Plan.create({
            'name': 'Monthly Plan',
            'billing_interval': BILLING_INTERVAL_MONTHLY,
            'billing_price': 800.0,
        })
        self.assertEqual(monthly_plan.compute_next_billing_date(base_date), date(2026, 2, 15))

        yearly_plan = self.Plan.create({
            'name': 'Yearly Plan',
            'billing_interval': BILLING_INTERVAL_YEARLY,
            'billing_price': 8000.0,
        })
        self.assertEqual(yearly_plan.compute_next_billing_date(base_date), date(2027, 1, 15))

    def test_minimum_quantity_validation(self):
        """Minimum quantity must be at least 1."""
        with self.assertRaises(ValidationError):
            self.Plan.create({
                'name': 'Zero Seats Plan',
                'billing_price': 50.0,
                'minimum_quantity': 0,
            })

    def test_negative_billing_price_rejected(self):
        """Negative billing price must raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.Plan.create({
                'name': 'Negative Plan',
                'billing_price': -10.0,
            })

    def test_invalid_availability_dates_rejected(self):
        """End date earlier than start date must raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.Plan.create({
                'name': 'Invalid Date Plan',
                'billing_price': 100.0,
                'start_date': date(2026, 6, 1),
                'end_date': date(2026, 5, 1),
            })

    def test_governance_permissions_defaults_and_toggles(self):
        """Verify governance flags can be configured per plan."""
        plan = self.Plan.create({
            'name': 'Strict Annual Contract',
            'billing_price': 12000.0,
            'billing_interval': BILLING_INTERVAL_YEARLY,
            'auto_close': True,
            'allow_early_close': False,
            'allow_pause': False,
            'allow_renewal': False,
        })
        self.assertTrue(plan.auto_close)
        self.assertFalse(plan.allow_early_close)
        self.assertFalse(plan.allow_pause)
        self.assertFalse(plan.allow_renewal)
