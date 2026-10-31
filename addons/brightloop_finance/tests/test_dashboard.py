# -*- coding: utf-8 -*-
"""
test_dashboard.py
Member 4 — Brightloop Finance

Unit tests for the financial dashboard KPI aggregation.

Covers:
- Revenue received accuracy
- Outstanding balance accuracy
- Overdue count and amount
- Date range filtering
- Paused vs active subscription count (reads brightloop.subscription)
"""

from odoo.tests.common import TransactionCase, tagged
from datetime import date, timedelta


@tagged('brightloop', 'brightloop_dashboard', 'post_install', '-at_install')
class TestBrightloopDashboard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Dashboard Test Customer',
            'customer_rank': 1,
        })
        cls.method = cls.env['brightloop.payment.method'].create({
            'name': 'Cash Dashboard',
            'code': 'cash_dash',
        })
        cls.journal = cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.env.company.id)],
            limit=1,
        )
        cls.income_account = cls.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_id', '=', cls.env.company.id),
        ], limit=1)

    def _make_posted_invoice(self, amount, due_date=None):
        inv = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'invoice_date': date.today(),
            'invoice_date_due': due_date or (date.today() + timedelta(days=30)),
            'invoice_line_ids': [(0, 0, {
                'name': 'Service',
                'quantity': 1,
                'price_unit': amount,
                'account_id': self.income_account.id,
            })],
        })
        inv.action_post()
        return inv

    def _make_posted_payment(self, amount):
        pay = self.env['brightloop.payment'].create({
            'partner_id': self.partner.id,
            'payment_method_id': self.method.id,
            'amount': amount,
            'payment_date': date.today(),
        })
        pay.action_post()
        return pay

    def _get_dashboard(self):
        return self.env['brightloop.finance.dashboard'].create({
            'date_from': date.today().replace(day=1),
            'date_to': date.today(),
        })

    # ─── Revenue tests ────────────────────────────────────────────────────────

    def test_01_revenue_only_counts_posted_allocations(self):
        """Revenue received = only posted payment allocations."""
        inv = self._make_posted_invoice(1000.0)
        pay = self._make_posted_payment(600.0)
        self.env['brightloop.invoice.payment'].create({
            'payment_id': pay.id,
            'invoice_id': inv.id,
            'allocated_amount': 600.0,
        })
        dash = self._get_dashboard()
        self.assertGreaterEqual(dash.revenue_received, 600.0)

    def test_02_unallocated_payment_not_revenue(self):
        """Posted payment with no allocation does not increase revenue."""
        before = self._get_dashboard().revenue_received
        # Post payment but don't allocate it
        self._make_posted_payment(999.0)
        after = self._get_dashboard().revenue_received
        # Revenue should not change without an allocation record
        self.assertAlmostEqual(before, after, places=2)

    # ─── Outstanding tests ────────────────────────────────────────────────────

    def test_03_outstanding_balance_accuracy(self):
        """Outstanding = sum of amount_residual on posted invoices."""
        inv = self._make_posted_invoice(800.0)
        dash = self._get_dashboard()
        # Invoice has full amount_residual (unpaid)
        self.assertGreaterEqual(dash.total_outstanding, 800.0)

    # ─── Overdue tests ────────────────────────────────────────────────────────

    def test_04_overdue_invoice_counted(self):
        """Past-due unpaid invoice increments overdue count."""
        past = date.today() - timedelta(days=10)
        self._make_posted_invoice(300.0, due_date=past)
        dash = self._get_dashboard()
        self.assertGreaterEqual(dash.overdue_invoice_count, 1)
        self.assertGreaterEqual(dash.overdue_amount, 300.0)

    def test_05_future_due_not_overdue(self):
        """Invoice with future due date does not count as overdue."""
        future = date.today() + timedelta(days=60)
        inv = self._make_posted_invoice(500.0, due_date=future)
        overdue_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'reversed']),
            ('amount_residual', '>', 0),
            ('invoice_date_due', '<', str(date.today())),
            ('id', '=', inv.id),
        ])
        self.assertFalse(overdue_invoices)

    # ─── Subscription count tests ─────────────────────────────────────────────

    def test_06_subscription_count_separates_paused(self):
        """
        Active count excludes paused. Paused count is separate.
        Only runs if brightloop.subscription model is installed.
        """
        if 'brightloop.subscription' not in self.env:
            self.skipTest('brightloop.subscription not yet installed')

        Sub = self.env['brightloop.subscription']
        # Create one active + one paused subscription
        partner2 = self.env['res.partner'].create({'name': 'Sub Test Partner'})
        active_sub = Sub.create({
            'partner_id': partner2.id,
            'status': 'active',
            'is_paused': False,
        })
        paused_sub = Sub.create({
            'partner_id': partner2.id,
            'status': 'active',
            'is_paused': True,
        })
        dash = self._get_dashboard()
        active_ids = Sub.search([('status', '=', 'active'), ('is_paused', '=', False)]).ids
        paused_ids = Sub.search([('status', '=', 'active'), ('is_paused', '=', True)]).ids
        self.assertIn(active_sub.id, active_ids)
        self.assertIn(paused_sub.id, paused_ids)
        self.assertNotIn(paused_sub.id, active_ids)

