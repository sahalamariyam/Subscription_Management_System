# -*- coding: utf-8 -*-
"""
test_payment.py
Member 4 — Brightloop Finance

Unit tests for:
- Payment recording
- Amount validation
- Duplicate reference prevention
- Payment lifecycle (draft → posted → cancelled → draft)
- Payment method reference requirements

Run with:
    ./odoo-bin -d <db> --test-enable -i brightloop_finance
"""

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError
from datetime import date


@tagged('brightloop', 'brightloop_payment', 'post_install', '-at_install')
class TestBrightloopPayment(TransactionCase):
    """Tests for brightloop.payment model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a test customer
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer BL4',
            'customer_rank': 1,
        })

        # Create payment methods
        cls.method_cash = cls.env['brightloop.payment.method'].create({
            'name': 'Cash Test',
            'code': 'cash_test',
            'requires_reference': False,
        })
        cls.method_bank = cls.env['brightloop.payment.method'].create({
            'name': 'Bank Transfer Test',
            'code': 'bank_test',
            'requires_reference': True,
        })

    def _make_payment(self, amount=100.0, method=None, reference=None,
                       payment_date=None, notes=None):
        """Helper: create a draft payment."""
        return self.env['brightloop.payment'].create({
            'partner_id': self.partner.id,
            'payment_method_id': (method or self.method_cash).id,
            'amount': amount,
            'payment_date': payment_date or date.today(),
            'reference': reference,
            'notes': notes,
        })

    # ─── Basic recording tests ────────────────────────────────────────────────
    def test_01_create_payment_draft(self):
        """New payments default to draft state."""
        p = self._make_payment(amount=500.0)
        self.assertEqual(p.state, 'draft')
        self.assertNotEqual(p.name, 'New', 'Sequence should be assigned on create.')

    def test_02_post_payment(self):
        """Draft payment can be posted."""
        p = self._make_payment(amount=250.0)
        p.action_post()
        self.assertEqual(p.state, 'posted')

    def test_03_cancel_payment(self):
        """Posted payment without allocations can be cancelled."""
        p = self._make_payment()
        p.action_post()
        p.action_cancel()
        self.assertEqual(p.state, 'cancelled')

    def test_04_reset_to_draft(self):
        """Cancelled payment can be reset to draft."""
        p = self._make_payment()
        p.action_post()
        p.action_cancel()
        p.action_reset_to_draft()
        self.assertEqual(p.state, 'draft')

    def test_05_cannot_post_from_cancelled(self):
        """Cancelled payment cannot be posted directly."""
        p = self._make_payment()
        p.action_post()
        p.action_cancel()
        with self.assertRaises(UserError):
            p.action_post()

    # ─── Amount validation ────────────────────────────────────────────────────
    def test_06_zero_amount_rejected(self):
        """Zero amount should raise ValidationError."""
        with self.assertRaises(Exception):
            self._make_payment(amount=0)

    def test_07_negative_amount_rejected(self):
        """Negative amount should raise ValidationError."""
        with self.assertRaises(Exception):
            self._make_payment(amount=-50)

    # ─── Reference requirements ───────────────────────────────────────────────
    def test_08_bank_transfer_requires_reference(self):
        """Payment method requiring reference raises error when missing."""
        with self.assertRaises(ValidationError):
            p = self._make_payment(method=self.method_bank, reference=None)
            p._check_reference_required()

    def test_09_bank_transfer_with_reference_ok(self):
        """Payment method requiring reference succeeds when provided."""
        p = self._make_payment(method=self.method_bank, reference='TXN-001')
        self.assertTrue(p.id)

    # ─── Duplicate prevention ─────────────────────────────────────────────────
    def test_10_duplicate_reference_rejected(self):
        """Two payments with same method + reference should fail unique constraint."""
        self._make_payment(method=self.method_bank, reference='TXN-DUPE-001')
        with self.assertRaises(Exception):
            self._make_payment(method=self.method_bank, reference='TXN-DUPE-001')

    def test_11_same_reference_different_method_ok(self):
        """Same reference on different payment methods is allowed."""
        p1 = self._make_payment(method=self.method_bank, reference='REF-MULTI')
        p2 = self._make_payment(method=self.method_cash, reference='REF-MULTI')
        self.assertTrue(p1.id and p2.id)


@tagged('brightloop', 'brightloop_allocation', 'post_install', '-at_install')
class TestBrightloopAllocation(TransactionCase):
    """Tests for brightloop.invoice.payment allocation model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer Alloc',
            'customer_rank': 1,
        })
        cls.method_cash = cls.env['brightloop.payment.method'].create({
            'name': 'Cash Alloc',
            'code': 'cash_alloc',
        })

        # Note: invoice tests require brightloop.invoice (Member 3).
        # These are stub tests; full integration tests run after Member 3 merges.
        # Skipping invoice-dependent assertions for now.

    def test_01_allocation_module_exists(self):
        """Allocation model is registered."""
        self.assertIn('brightloop.invoice.payment', self.env)

    def test_02_payment_model_exists(self):
        """Payment model is registered."""
        self.assertIn('brightloop.payment', self.env)

    def test_03_payment_method_model_exists(self):
        """Payment method model is registered."""
        self.assertIn('brightloop.payment.method', self.env)

    def test_04_dashboard_model_exists(self):
        """Dashboard model is registered."""
        self.assertIn('brightloop.finance.dashboard', self.env)
