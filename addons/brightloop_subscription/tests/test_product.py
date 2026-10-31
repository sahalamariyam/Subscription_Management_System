# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Product & Variant Unit Tests
Owner: Member 2 (Product, Plan, Quotation & Subscription Lifecycle Lead)

Validates:
- Product creation and editing.
- Rejection of invalid or negative sales and cost prices.
- Variant price adjustments.
- Official example: Base price 5000 + Odoo Brand 560 = 5560.
- Rejection of variant adjustments that produce negative total price.
"""

from odoo.tests import common
from odoo.exceptions import ValidationError


class TestBrightloopProduct(common.TransactionCase):
    """Test product creation, variant price adjustment, and validations."""

    def setUp(self):
        super().setUp()
        self.Product = self.env['brightloop.product']
        self.Variant = self.env['brightloop.product.variant']

    def test_product_creation_and_editing(self):
        """Test valid product creation and field updates."""
        product = self.Product.create({
            'name': 'Cloud Business Suite',
            'product_type': 'software',
            'sales_price': 5000.0,
            'cost_price': 1200.0,
            'notes': 'Flagship multi-tenant software subscription',
        })
        self.assertTrue(product.id)
        self.assertEqual(product.name, 'Cloud Business Suite')
        self.assertEqual(product.product_type, 'software')
        self.assertEqual(product.sales_price, 5000.0)
        self.assertEqual(product.cost_price, 1200.0)
        self.assertTrue(product.active)

        # Edit product
        product.write({
            'sales_price': 5200.0,
            'notes': 'Updated pricing for Q4',
        })
        self.assertEqual(product.sales_price, 5200.0)
        self.assertEqual(product.notes, 'Updated pricing for Q4')

    def test_negative_sales_price_rejected(self):
        """Negative sales price must raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.Product.create({
                'name': 'Invalid Software',
                'product_type': 'software',
                'sales_price': -100.0,
            })

    def test_negative_cost_price_rejected(self):
        """Negative cost price must raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.Product.create({
                'name': 'Invalid Cost Software',
                'product_type': 'software',
                'sales_price': 500.0,
                'cost_price': -50.0,
            })

    def test_official_variant_price_calculation(self):
        """
        Official requirement validation:
        A product has a base price of 5,000. Selecting the Odoo brand variant adds 560.
        Final price = 5,000 + 560 = 5,560.
        """
        product = self.Product.create({
            'name': 'Brightloop ERP Core',
            'product_type': 'software',
            'sales_price': 5000.0,
            'cost_price': 1500.0,
        })
        variant_odoo = self.Variant.create({
            'product_id': product.id,
            'name': 'Odoo Brand',
            'price_adjustment': 560.0,
        })
        self.assertEqual(variant_odoo.effective_price, 5560.0)
        self.assertEqual(variant_odoo.display_name, 'Brightloop ERP Core (Odoo Brand)')

    def test_negative_variant_adjustment_below_zero_rejected(self):
        """Variant discount exceeding base price must raise ValidationError."""
        product = self.Product.create({
            'name': 'Standard Add-on',
            'product_type': 'addon',
            'sales_price': 100.0,
        })
        with self.assertRaises(ValidationError):
            self.Variant.create({
                'product_id': product.id,
                'name': 'Excessive Discount',
                'price_adjustment': -150.0,
            })

    def test_valid_discounted_variant_price(self):
        """Variant discount that remains non-negative is permitted."""
        product = self.Product.create({
            'name': 'Professional Service',
            'product_type': 'service',
            'sales_price': 1000.0,
        })
        variant = self.Variant.create({
            'product_id': product.id,
            'name': 'Promotional Edition',
            'price_adjustment': -200.0,
        })
        self.assertEqual(variant.effective_price, 800.0)
