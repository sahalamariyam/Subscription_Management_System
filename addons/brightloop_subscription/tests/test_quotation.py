# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Quotation Unit Tests
Owner: Member 2 (Product, Plan, Quotation & Subscription Lifecycle Lead)

Validates:
- Quotation template creation and template product lines.
- Quotation validity period and expiration dates.
- Instant quotation generation from templates.
- Rejection of expired quotation confirmation.
- Minimum quantity enforcement from the associated plan.
- Accurate line calculations and customer association.
"""

from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests import common
from odoo.exceptions import ValidationError, UserError


class TestBrightloopQuotation(common.TransactionCase):
    """Test quotation templates, validity checks, and customer quotation creation."""

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.Product = self.env['brightloop.product']
        self.Variant = self.env['brightloop.product.variant']
        self.Plan = self.env['brightloop.plan']
        self.Template = self.env['brightloop.quotation.template']
        self.Subscription = self.env['brightloop.subscription']

        # Setup base customer
        self.customer = self.Partner.create({
            'name': 'Acme Corporation',
            'email': 'procurement@acme.test',
        })

        # Setup base product & variant
        self.product = self.Product.create({
            'name': 'Cloud Platform Enterprise',
            'product_type': 'software',
            'sales_price': 5000.0,
            'cost_price': 1000.0,
        })
        self.variant = self.Variant.create({
            'product_id': self.product.id,
            'name': 'Odoo Brand',
            'price_adjustment': 560.0,
        })

        # Setup plan
        self.plan = self.Plan.create({
            'name': 'Standard Monthly Plan',
            'billing_interval': 'monthly',
            'billing_price': 5560.0,
            'minimum_quantity': 2,
        })

    def test_quotation_template_creation(self):
        """Create a quotation template with lines and verify properties."""
        template = self.Template.create({
            'name': 'Enterprise Starter Template',
            'plan_id': self.plan.id,
            'validity_days': 15,
            'line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'variant_id': self.variant.id,
                    'quantity': 2.0,
                    'unit_price': 5560.0,
                    'tax_id': 'GST_18',
                })
            ]
        })
        self.assertTrue(template.id)
        self.assertEqual(len(template.line_ids), 1)
        self.assertEqual(template.line_ids[0].quantity, 2.0)
        self.assertEqual(template.line_ids[0].unit_price, 5560.0)

    def test_generate_quotation_from_template(self):
        """Sales rep generates a customer quotation directly from a template."""
        template = self.Template.create({
            'name': 'Enterprise Starter Template',
            'plan_id': self.plan.id,
            'validity_days': 20,
            'line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'variant_id': self.variant.id,
                    'quantity': 3.0,
                    'unit_price': 5560.0,
                    'tax_id': 'GST_18',
                })
            ]
        })
        quote = template.action_generate_quotation_for_customer(self.customer.id)
        self.assertEqual(quote.status, 'quotation')
        self.assertEqual(quote.partner_id, self.customer)
        self.assertEqual(quote.plan_id, self.plan)
        self.assertEqual(len(quote.line_ids), 1)
        self.assertEqual(quote.amount_total, 3.0 * 5560.0)
        self.assertEqual(quote.valid_until, date.today() + relativedelta(days=20))

    def test_expired_quotation_confirmation_rejected(self):
        """Confirming an expired quotation must raise ValidationError."""
        quote = self.Subscription.create({
            'partner_id': self.customer.id,
            'plan_id': self.plan.id,
            'status': 'draft',
            'valid_until': date.today() - relativedelta(days=1),
            'line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'quantity': 2.0,
                    'unit_price': 5000.0,
                })
            ]
        })
        # Move to quotation status
        quote.action_send_quotation()
        self.assertEqual(quote.status, 'quotation')

        # Set valid_until explicitly to yesterday to simulate expired quote
        quote.valid_until = date.today() - relativedelta(days=1)

        with self.assertRaises(ValidationError):
            quote.action_confirm()

    def test_quotation_enforces_plan_minimum_quantity(self):
        """Quotation with total quantity below plan minimum is rejected."""
        quote = self.Subscription.create({
            'partner_id': self.customer.id,
            'plan_id': self.plan.id,  # Requires minimum_quantity = 2
            'status': 'draft',
            'line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'quantity': 1.0,  # Below minimum 2
                    'unit_price': 5000.0,
                })
            ]
        })
        with self.assertRaises(ValidationError):
            quote.action_send_quotation()
