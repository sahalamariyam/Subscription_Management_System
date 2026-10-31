# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Recurring Billing Engine Unit Tests
Owner: Member 3 (Billing, Invoice Management, Tax & Discount Lead)

Covers all 12 Phase 2 test specifications:
1. Invoice generation from an active subscription.
2. Correct partner and subscription linkage.
3. Correct invoice line quantities and prices.
4. Percentage discount calculation.
5. Fixed discount calculation.
6. Combined percentage and fixed discount.
7. Tax assignment.
8. Correct billing period boundaries.
9. Correct next billing date advancement.
10. Duplicate billing prevention.
11. Failed invoice creation does not advance the subscription date.
12. One subscription failure does not stop the entire batch.
"""

from datetime import date
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import common
from odoo.exceptions import ValidationError, UserError
from odoo.addons.brightloop_core.models.shared_constants import (
    SUBSCRIPTION_STATUS_DRAFT,
    SUBSCRIPTION_STATUS_ACTIVE,
)


class TestBrightloopBillingEngine(common.TransactionCase):
    """Test suite for recurring billing engine, invoice generation, discounts, taxes, and atomicity."""

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.Product = self.env['brightloop.product']
        self.Plan = self.env['brightloop.plan']
        self.Subscription = self.env['brightloop.subscription']
        self.BillingEngine = self.env['brightloop.billing.engine']
        self.BillingJob = self.env['brightloop.billing.job']
        self.AccountMove = self.env['account.move']
        self.AccountTax = self.env['account.tax']
        self.PaymentTerm = self.env['account.payment.term']

        self.company = self.env.company
        self.customer = self.Partner.create({
            'name': 'Acme Enterprise Ltd',
            'email': 'billing@acme.test',
        })

        self.product = self.Product.create({
            'name': 'Cloud Platform Enterprise',
            'product_type': 'software',
            'sales_price': 1000.0,
        })

        self.plan = self.Plan.create({
            'name': 'Monthly Standard Plan',
            'billing_interval': 'monthly',
            'billing_interval_count': 1,
            'billing_price': 1000.0,
            'allow_pause': True,
            'allow_renewal': True,
            'allow_early_close': True,
        })

    def _create_active_subscription(self, **kwargs):
        """Helper to create and activate a subscription for testing."""
        target_billing_date = kwargs.pop('next_billing_date', date(2026, 5, 1))
        lines_data = kwargs.pop('lines', [
            {
                'product_id': self.product.id,
                'quantity': 1.0,
                'unit_price': 1000.0,
            }
        ])
        vals = {
            'partner_id': self.customer.id,
            'plan_id': self.plan.id,
            'status': SUBSCRIPTION_STATUS_DRAFT,
            'payment_terms': 'Immediate Payment',
            'line_ids': [(0, 0, l_val) for l_val in lines_data],
        }
        vals.update(kwargs)
        sub = self.Subscription.create(vals)

        # Progress lifecycle: Draft -> Quotation -> Confirmed -> Active
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_activate()

        # Set specific billing test dates
        sub.write({
            'next_billing_date': target_billing_date,
            'billing_anchor_day': target_billing_date.day,
        })
        return sub

    def test_01_invoice_generation_from_active_subscription(self):
        """1. Invoice generation from an active subscription."""
        target_date = date(2026, 5, 1)
        sub = self._create_active_subscription(next_billing_date=target_date)

        summary = self.BillingEngine.run_billing_engine(billing_date=target_date)
        self.assertEqual(summary['processed'], 1)
        self.assertEqual(summary['succeeded'], 1)
        self.assertEqual(summary['failed'], 0)

        job = self.BillingJob.search([('subscription_id', '=', sub.id)])
        self.assertEqual(len(job), 1)
        self.assertEqual(job.state, 'done')
        self.assertTrue(job.invoice_id)
        self.assertEqual(job.invoice_id.move_type, 'out_invoice')
        self.assertEqual(job.invoice_id.state, 'draft')

    def test_02_correct_partner_and_subscription_linkage(self):
        """2. Correct partner and subscription linkage on move and billing job."""
        target_date = date(2026, 5, 1)
        sub = self._create_active_subscription(next_billing_date=target_date)

        self.BillingEngine.run_billing_engine(billing_date=target_date)
        job = self.BillingJob.search([('subscription_id', '=', sub.id)], limit=1)
        invoice = job.invoice_id

        self.assertEqual(invoice.partner_id, self.customer)
        self.assertEqual(invoice.subscription_id, sub)
        self.assertEqual(job.subscription_id, sub)
        self.assertEqual(job.company_id, sub.company_id)

    def test_03_correct_invoice_line_quantities_and_prices(self):
        """3. Correct invoice line quantities, prices, and unset native product_id."""
        target_date = date(2026, 5, 1)
        sub = self._create_active_subscription(
            next_billing_date=target_date,
            lines=[
                {
                    'product_id': self.product.id,
                    'name': 'Custom Enterprise Cloud Suite',
                    'quantity': 3.0,
                    'unit_price': 250.0,
                }
            ],
        )

        self.BillingEngine.run_billing_engine(billing_date=target_date)
        job = self.BillingJob.search([('subscription_id', '=', sub.id)], limit=1)
        invoice = job.invoice_id

        self.assertEqual(len(invoice.invoice_line_ids), 1)
        inv_line = invoice.invoice_line_ids[0]
        self.assertEqual(inv_line.name, 'Custom Enterprise Cloud Suite')
        self.assertEqual(inv_line.quantity, 3.0)
        self.assertEqual(inv_line.price_unit, 250.0)
        # Verify native product_id is unset
        self.assertFalse(inv_line.product_id)

    def test_04_percentage_discount_calculation(self):
        """4. Percentage discount calculation and line mapping."""
        # Direct formula test
        disc = self.BillingEngine._calculate_effective_discount(
            unit_price=100.0, quantity=1.0, percentage_discount=15.0, fixed_discount=0.0
        )
        self.assertEqual(disc, 15.0)

        # End-to-end invoice generation test
        target_date = date(2026, 5, 1)
        sub = self._create_active_subscription(
            next_billing_date=target_date,
            lines=[
                {
                    'product_id': self.product.id,
                    'quantity': 2.0,
                    'unit_price': 500.0,
                    'discount': 15.0,
                    'discount_amount': 0.0,
                }
            ],
        )
        self.BillingEngine.run_billing_engine(billing_date=target_date)
        job = self.BillingJob.search([('subscription_id', '=', sub.id)], limit=1)
        inv_line = job.invoice_id.invoice_line_ids[0]
        self.assertEqual(inv_line.discount, 15.0)

    def test_05_fixed_discount_calculation(self):
        """5. Fixed discount calculation converted to effective percentage."""
        # unit_price=100.0, quantity=2.0, fixed_discount=40.0
        # gross = 200, net = 160 -> effective discount = 20.0%
        disc = self.BillingEngine._calculate_effective_discount(
            unit_price=100.0, quantity=2.0, percentage_discount=0.0, fixed_discount=40.0
        )
        self.assertEqual(disc, 20.0)

        target_date = date(2026, 5, 1)
        sub = self._create_active_subscription(
            next_billing_date=target_date,
            lines=[
                {
                    'product_id': self.product.id,
                    'quantity': 2.0,
                    'unit_price': 100.0,
                    'discount': 0.0,
                    'discount_amount': 40.0,
                }
            ],
        )
        self.BillingEngine.run_billing_engine(billing_date=target_date)
        job = self.BillingJob.search([('subscription_id', '=', sub.id)], limit=1)
        inv_line = job.invoice_id.invoice_line_ids[0]
        self.assertEqual(inv_line.discount, 20.0)

    def test_06_combined_percentage_and_fixed_discount(self):
        """6. Combined percentage and fixed discount."""
        # unit_price=1000.0, quantity=2.0, percentage=10%, fixed=50.0
        # net_before_fixed = 900
        # net_unit_price = 900 - 25 = 875
        # effective_discount = 100 * (1 - 875/1000) = 12.5%
        disc = self.BillingEngine._calculate_effective_discount(
            unit_price=1000.0, quantity=2.0, percentage_discount=10.0, fixed_discount=50.0
        )
        self.assertEqual(disc, 12.5)

        target_date = date(2026, 5, 1)
        sub = self._create_active_subscription(
            next_billing_date=target_date,
            lines=[
                {
                    'product_id': self.product.id,
                    'quantity': 2.0,
                    'unit_price': 1000.0,
                    'discount': 10.0,
                    'discount_amount': 50.0,
                }
            ],
        )
        self.BillingEngine.run_billing_engine(billing_date=target_date)
        job = self.BillingJob.search([('subscription_id', '=', sub.id)], limit=1)
        inv_line = job.invoice_id.invoice_line_ids[0]
        self.assertEqual(inv_line.discount, 12.5)

    def test_07_tax_assignment(self):
        """7. Native tax assignment via fields.Command.set()."""
        tax = self.AccountTax.create({
            'name': 'Test VAT 18%',
            'amount_type': 'percent',
            'amount': 18.0,
            'type_tax_use': 'sale',
            'company_id': self.company.id,
        })

        target_date = date(2026, 5, 1)
        sub = self._create_active_subscription(
            next_billing_date=target_date,
            lines=[
                {
                    'product_id': self.product.id,
                    'quantity': 1.0,
                    'unit_price': 1000.0,
                    'tax_ids': [fields.Command.set([tax.id])],
                }
            ],
        )
        self.BillingEngine.run_billing_engine(billing_date=target_date)
        job = self.BillingJob.search([('subscription_id', '=', sub.id)], limit=1)
        inv_line = job.invoice_id.invoice_line_ids[0]
        self.assertIn(tax, inv_line.tax_ids)

    def test_08_correct_billing_period_boundaries(self):
        """8. Correct billing period boundaries (period_start to 1 day before next cycle)."""
        target_date = date(2026, 5, 1)
        sub = self._create_active_subscription(next_billing_date=target_date)

        self.BillingEngine.run_billing_engine(billing_date=target_date)
        job = self.BillingJob.search([('subscription_id', '=', sub.id)], limit=1)

        self.assertEqual(job.billing_period_start, date(2026, 5, 1))
        # Monthly next cycle from May 1 is June 1 -> period end is May 31
        self.assertEqual(job.billing_period_end, date(2026, 5, 31))

    def test_09_correct_next_billing_date_advancement(self):
        """9. Correct next billing date advancement preserving anchor day."""
        target_date = date(2026, 5, 31)
        sub = self._create_active_subscription(next_billing_date=target_date)
        sub.write({'billing_anchor_day': 31})

        self.BillingEngine.run_billing_engine(billing_date=target_date)

        # For monthly plan with anchor 31: May 31 -> June 30
        self.assertEqual(sub.next_billing_date, date(2026, 6, 30))
        self.assertEqual(sub.billing_anchor_day, 31)

    def test_10_duplicate_billing_prevention(self):
        """10. Duplicate billing prevention via idempotency key and Billing Job state."""
        target_date = date(2026, 5, 1)
        sub = self._create_active_subscription(next_billing_date=target_date)

        # First run creates invoice and job
        summary1 = self.BillingEngine.run_billing_engine(billing_date=target_date)
        self.assertEqual(summary1['succeeded'], 1)
        self.assertEqual(len(summary1['invoice_ids']), 1)

        # Manually reset next_billing_date to target_date to simulate accidental duplicate trigger
        sub.write({'next_billing_date': target_date})

        # Second run must detect completed job with same idempotency key and skip
        summary2 = self.BillingEngine.run_billing_engine(billing_date=target_date)
        self.assertEqual(summary2['succeeded'], 0)
        self.assertEqual(summary2['skipped'], 1)
        self.assertEqual(len(summary2['invoice_ids']), 0)

        # Ensure only 1 job exists for this period
        jobs = self.BillingJob.search([('subscription_id', '=', sub.id)])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs.state, 'done')

    def test_11_failed_invoice_creation_does_not_advance_subscription_date(self):
        """11. Failed invoice creation rolls back and does not advance next_billing_date."""
        target_date = date(2026, 5, 1)
        sub = self._create_active_subscription(next_billing_date=target_date)

        def _failing_invoice_create(engine_self, sub_param, p_start, p_end):
            raise ValidationError("Simulated accounting ledger failure during invoice creation")

        BillingEngineModel = type(self.env['brightloop.billing.engine'])
        with patch.object(BillingEngineModel, '_create_invoice_for_subscription', _failing_invoice_create):
            summary = self.env['brightloop.billing.engine'].run_billing_engine(billing_date=target_date)

        self.assertEqual(summary['failed'], 1)
        self.assertEqual(summary['succeeded'], 0)

        # Assert next_billing_date was NOT advanced
        sub.invalidate_recordset()
        self.assertEqual(sub.next_billing_date, target_date)

        # Assert billing job recorded the failure
        job = self.BillingJob.search([('subscription_id', '=', sub.id)], limit=1)
        self.assertTrue(job)
        self.assertEqual(job.state, 'failed')
        self.assertIn("Simulated accounting ledger failure", job.error_message)
        self.assertFalse(job.invoice_id)

    def test_12_one_subscription_failure_does_not_stop_batch(self):
        """12. One subscription failure does not prevent processing other subscriptions."""
        target_date = date(2026, 5, 1)
        # Create Sub 1 (will be rigged to fail)
        sub1 = self._create_active_subscription(next_billing_date=target_date)

        # Create Sub 2 (valid)
        customer2 = self.Partner.create({'name': 'Beta Corp', 'email': 'beta@corp.test'})
        sub2 = self._create_active_subscription(
            partner_id=customer2.id,
            next_billing_date=target_date,
        )

        sub1_id = sub1.id
        BillingEngineModel = type(self.env['brightloop.billing.engine'])
        original_create = BillingEngineModel._create_invoice_for_subscription

        def _conditional_create(engine_self, sub_param, p_start, p_end):
            if sub_param.id == sub1_id:
                raise ValidationError("Simulated failure for Sub 1")
            return original_create(engine_self, sub_param, p_start, p_end)

        with patch.object(BillingEngineModel, '_create_invoice_for_subscription', _conditional_create):
            summary = self.env['brightloop.billing.engine'].run_billing_engine(billing_date=target_date)

        self.assertEqual(summary['processed'], 2)
        self.assertEqual(summary['failed'], 1)
        self.assertEqual(summary['succeeded'], 1)

        # Sub 1 failed, date not advanced
        job1 = self.BillingJob.search([('subscription_id', '=', sub1.id)], limit=1)
        self.assertEqual(job1.state, 'failed')
        sub1.invalidate_recordset()
        self.assertEqual(sub1.next_billing_date, target_date)

        # Sub 2 succeeded, date advanced, invoice created
        job2 = self.BillingJob.search([('subscription_id', '=', sub2.id)], limit=1)
        self.assertEqual(job2.state, 'done')
        self.assertTrue(job2.invoice_id)
        sub2.invalidate_recordset()
        self.assertEqual(sub2.next_billing_date, date(2026, 6, 1))

    def test_13_billing_job_deletion_prohibited(self):
        """13. Billing jobs are permanent audit records; deletion is prohibited via unlink()."""
        target_date = date(2026, 5, 1)
        sub = self._create_active_subscription(next_billing_date=target_date)
        self.BillingEngine.run_billing_engine(billing_date=target_date)

        job = self.BillingJob.search([('subscription_id', '=', sub.id)], limit=1)
        self.assertTrue(job)
        with self.assertRaises(UserError):
            job.unlink()
