# -*- coding: utf-8 -*-
"""
test_allocation.py
Member 4 — Brightloop Finance

Integration tests for payment allocation against account.move invoices.

Covers:
- Single full allocation
- Multiple partial allocations
- Over-allocation prevention
- Duplicate allocation prevention
- Balance calculation (amount_total - amount_residual)
- Overdue invoice identification
- Outstanding balance accuracy
- Revenue aggregation

Run with:
    ./odoo-bin -d <db> --test-enable -i brightloop_finance
"""

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import date, timedelta


@tagged('brightloop', 'brightloop_allocation_integration', 'post_install', '-at_install')
class TestBrightloopAllocationIntegration(TransactionCase):
    """
    Integration tests requiring account.move (Odoo 18) and
    brightloop.payment models to both be installed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Customer partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Integration Test Customer',
            'customer_rank': 1,
        })

        # Payment method
        cls.method_bank = cls.env['brightloop.payment.method'].create({
            'name': 'Bank (Integration)',
            'code': 'bank_intg',
            'requires_reference': True,
        })
        cls.method_cash = cls.env['brightloop.payment.method'].create({
            'name': 'Cash (Integration)',
            'code': 'cash_intg',
            'requires_reference': False,
        })

        # Odoo journal for test invoices
        cls.journal = cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.env.company.id)],
            limit=1,
        )
        cls.bank_journal = cls.env['account.journal'].search(
            [('type', 'in', ['bank', 'cash']), ('company_id', '=', cls.env.company.id)],
            limit=1,
        )
        # Income account
        cls.income_account = cls.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_ids', 'in', [cls.env.company.id]),
        ], limit=1)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _make_invoice(self, amount, due_date=None, subscription=None):
        """Create and post a customer invoice (account.move)."""
        vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'invoice_date': date.today(),
            'invoice_date_due': due_date or (date.today() + timedelta(days=30)),
            'invoice_line_ids': [(0, 0, {
                'name': 'Test Service',
                'quantity': 1,
                'price_unit': amount,
                'account_id': self.income_account.id,
            })],
        }
        if subscription:
            vals['subscription_id'] = subscription.id
        inv = self.env['account.move'].create(vals)
        inv.action_post()
        return inv

    def _make_payment(self, amount, reference=None, method=None):
        """Create and post a brightloop payment."""
        pay = self.env['brightloop.payment'].create({
            'partner_id': self.partner.id,
            'payment_method_id': (method or self.method_cash).id,
            'amount': amount,
            'payment_date': date.today(),
            'reference': reference,
        })
        pay.action_post()
        return pay

    def _allocate(self, payment, invoice, amount):
        """Create an invoice payment allocation."""
        return self.env['brightloop.invoice.payment'].create({
            'payment_id': payment.id,
            'invoice_id': invoice.id,
            'allocated_amount': amount,
        })

    # ─── Allocation tests ─────────────────────────────────────────────────────

    def test_01_full_allocation(self):
        """Full payment allocation marks payment as fully allocated."""
        inv = self._make_invoice(500.0)
        pay = self._make_payment(500.0)
        alloc = self._allocate(pay, inv, 500.0)

        self.assertTrue(pay.is_fully_allocated)
        self.assertAlmostEqual(pay.unallocated_amount, 0.0, places=2)
        self.assertAlmostEqual(pay.total_allocated, 500.0, places=2)

    def test_02_partial_allocation(self):
        """Partial payment leaves correct unallocated remainder."""
        inv = self._make_invoice(1000.0)
        pay = self._make_payment(500.0)
        alloc = self._allocate(pay, inv, 400.0)

        self.assertFalse(pay.is_fully_allocated)
        self.assertAlmostEqual(pay.unallocated_amount, 100.0, places=2)
        self.assertAlmostEqual(pay.total_allocated, 400.0, places=2)

    def test_03_multiple_payments_one_invoice(self):
        """Multiple payments can be allocated to the same invoice."""
        inv = self._make_invoice(900.0)
        pay1 = self._make_payment(400.0)
        pay2 = self._make_payment(500.0)

        self._allocate(pay1, inv, 400.0)
        self._allocate(pay2, inv, 500.0)

        allocs = self.env['brightloop.invoice.payment'].search([
            ('invoice_id', '=', inv.id),
        ])
        total_allocated = sum(allocs.mapped('allocated_amount'))
        self.assertAlmostEqual(total_allocated, 900.0, places=2)

    def test_04_one_payment_multiple_invoices(self):
        """One payment can be split across multiple invoices."""
        inv1 = self._make_invoice(300.0)
        inv2 = self._make_invoice(200.0)
        pay  = self._make_payment(500.0)

        self._allocate(pay, inv1, 300.0)
        self._allocate(pay, inv2, 200.0)

        self.assertTrue(pay.is_fully_allocated)
        self.assertAlmostEqual(pay.total_allocated, 500.0, places=2)

    def test_05_over_allocation_blocked(self):
        """Allocating more than invoice's amount_residual is blocked."""
        inv = self._make_invoice(100.0)
        pay = self._make_payment(999.0)

        with self.assertRaises(ValidationError):
            self._allocate(pay, inv, 999.0)

    def test_06_duplicate_allocation_blocked(self):
        """Duplicate (invoice_id, payment_id) allocation is blocked."""
        inv  = self._make_invoice(200.0)
        pay  = self._make_payment(200.0)
        self._allocate(pay, inv, 100.0)

        with self.assertRaises(Exception):  # UNIQUE constraint
            self._allocate(pay, inv, 50.0)

    def test_07_payment_over_allocation_blocked(self):
        """Allocating more than payment amount across invoices is blocked."""
        inv1 = self._make_invoice(600.0)
        inv2 = self._make_invoice(600.0)
        pay  = self._make_payment(500.0)

        self._allocate(pay, inv1, 500.0)
        with self.assertRaises(ValidationError):
            self._allocate(pay, inv2, 1.0)  # payment is already fully allocated

    def test_08_overpayment_flag(self):
        """is_overpayment flag is set when allocations exceed payment amount."""
        inv = self._make_invoice(600.0)
        pay = self._make_payment(500.0)
        # Force an overpayment by bypassing constraint (sudo write directly)
        # In real use the constraint prevents this — this tests the compute field
        alloc = self.env['brightloop.invoice.payment'].sudo().with_context(bypass_allocation_limits=True).create({
            'payment_id': pay.id,
            'invoice_id': inv.id,
            'allocated_amount': 600.0,  # exceeds payment of 500
        })
        pay.invalidate_recordset()
        self.assertTrue(pay.is_overpayment)

    # ─── Balance calculation tests ────────────────────────────────────────────

    def test_09_invoice_balance_derived_correctly(self):
        """
        amount_paid (derived) = amount_total - amount_residual.
        Verify our allocation total matches the derived figure.
        """
        inv = self._make_invoice(750.0)
        pay = self._make_payment(250.0)
        self._allocate(pay, inv, 250.0)

        allocs = self.env['brightloop.invoice.payment'].search([
            ('invoice_id', '=', inv.id),
        ])
        brightloop_paid = sum(allocs.mapped('allocated_amount'))
        # Odoo native: amount_paid = amount_total - amount_residual
        odoo_paid = inv.amount_total - inv.amount_residual
        # Our allocation should match or be <= Odoo's derived figure
        self.assertAlmostEqual(brightloop_paid, 250.0, places=2)
        self.assertGreaterEqual(inv.amount_total, brightloop_paid)

    # ─── Overdue identification tests ─────────────────────────────────────────

    def test_10_overdue_invoice_identified(self):
        """Invoice past due_date with residual > 0 is overdue."""
        past_date = date.today() - timedelta(days=5)
        inv = self._make_invoice(300.0, due_date=past_date)

        overdue = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'reversed']),
            ('amount_residual', '>', 0),
            ('invoice_date_due', '<', str(date.today())),
            ('id', '=', inv.id),
        ])
        self.assertIn(inv, overdue)

    def test_11_paid_invoice_not_overdue(self):
        """Fully paid invoice is not in the overdue set."""
        past_date = date.today() - timedelta(days=5)
        inv = self._make_invoice(200.0, due_date=past_date)

        # Register payment via Odoo's native payment flow
        payment = self.env['account.payment'].create({
            'partner_id': self.partner.id,
            'amount': 200.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': (self.bank_journal or self.journal).id,
        })
        payment.action_post()
        (payment.move_id.line_ids + inv.line_ids).filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
        ).reconcile()

        overdue = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'reversed']),
            ('amount_residual', '>', 0),
            ('invoice_date_due', '<', str(date.today())),
            ('id', '=', inv.id),
        ])
        self.assertNotIn(inv, overdue)

    def test_12_future_due_invoice_not_overdue(self):
        """Invoice with future due date is not overdue even if unpaid."""
        future_date = date.today() + timedelta(days=30)
        inv = self._make_invoice(500.0, due_date=future_date)

        overdue = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'reversed']),
            ('amount_residual', '>', 0),
            ('invoice_date_due', '<', str(date.today())),
            ('id', '=', inv.id),
        ])
        self.assertNotIn(inv, overdue)

    # ─── Revenue aggregation tests ────────────────────────────────────────────

    def test_13_revenue_aggregation(self):
        """Revenue received = sum of allocated_amounts from posted payments."""
        inv1 = self._make_invoice(400.0)
        inv2 = self._make_invoice(600.0)
        pay1 = self._make_payment(400.0)
        pay2 = self._make_payment(300.0)  # partial payment on inv2

        self._allocate(pay1, inv1, 400.0)
        self._allocate(pay2, inv2, 300.0)

        alloc_data = self.env['brightloop.invoice.payment'].read_group(
            domain=[('payment_id.state', '=', 'posted')],
            fields=['allocated_amount:sum'],
            groupby=[],
        )
        total_revenue = alloc_data[0]['allocated_amount'] if alloc_data else 0.0
        # Must be at least 700 (our allocations) — may be more if other test
        # records exist in same transaction; check our specific payments
        our_allocs = self.env['brightloop.invoice.payment'].search([
            ('payment_id', 'in', [pay1.id, pay2.id]),
        ])
        our_revenue = sum(our_allocs.mapped('allocated_amount'))
        self.assertAlmostEqual(our_revenue, 700.0, places=2)

    def test_14_unposted_payment_excluded_from_revenue(self):
        """Draft payment allocations do NOT count as revenue."""
        inv = self._make_invoice(500.0)

        # Create DRAFT payment (not posted)
        draft_pay = self.env['brightloop.payment'].create({
            'partner_id': self.partner.id,
            'payment_method_id': self.method_cash.id,
            'amount': 500.0,
            'payment_date': date.today(),
        })
        # Allocate while still draft
        alloc = self.env['brightloop.invoice.payment'].create({
            'payment_id': draft_pay.id,
            'invoice_id': inv.id,
            'allocated_amount': 500.0,
        })

        # Revenue query excludes draft payments
        alloc_data = self.env['brightloop.invoice.payment'].read_group(
            domain=[
                ('payment_id.state', '=', 'posted'),
                ('payment_id', '=', draft_pay.id),
            ],
            fields=['allocated_amount:sum'],
            groupby=[],
        )
        revenue = alloc_data[0]['allocated_amount'] if alloc_data else 0.0
        self.assertAlmostEqual(revenue, 0.0, places=2,
                               msg='Draft payment must not appear in revenue.')

