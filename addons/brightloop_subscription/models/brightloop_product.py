# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Product & Variant Models
Owner: Member 2 (Product, Plan, Quotation & Subscription Lifecycle Lead)

Implements:
- Product creation, editing, and management with name, type, sales price, cost price, and notes.
- Product variants with configurable price adjustments.
- Effective price calculation: base sales price + variant price adjustment.
- Strict price validation (non-negative sales/cost price, non-negative adjusted price).
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BrightloopProduct(models.Model):
    _name = 'brightloop.product'
    _description = 'Brightloop Product'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(
        string='Product Name',
        required=True,
        tracking=True,
        help="Name of the software, add-on, or service product",
    )
    product_type = fields.Selection(
        selection=[
            ('software', 'Software'),
            ('addon', 'Add-on'),
            ('service', 'Service'),
        ],
        string='Product Type',
        default='software',
        required=True,
        tracking=True,
        help="Category of the commercial product",
    )
    sales_price = fields.Float(
        string='Sales Price',
        digits=(16, 2),
        required=True,
        default=0.0,
        tracking=True,
        help="Base sales price before variant adjustments",
    )
    cost_price = fields.Float(
        string='Cost Price',
        digits=(16, 2),
        default=0.0,
        tracking=True,
        help="Internal cost price for margin calculation",
    )
    notes = fields.Text(
        string='Notes',
        help="Internal product notes or specifications",
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archived products will not be available for new quotations",
    )
    variant_ids = fields.One2many(
        'brightloop.product.variant',
        'product_id',
        string='Product Variants',
        help="Configurable product variants with price adjustments",
    )

    @api.constrains('sales_price', 'cost_price')
    def _check_prices(self):
        for product in self:
            if product.sales_price < 0.0:
                raise ValidationError(_("Sales price cannot be negative."))
            if product.cost_price < 0.0:
                raise ValidationError(_("Cost price cannot be negative."))


class BrightloopProductVariant(models.Model):
    _name = 'brightloop.product.variant'
    _description = 'Brightloop Product Variant'
    _order = 'product_id, name'

    product_id = fields.Many2one(
        'brightloop.product',
        string='Product',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(
        string='Variant Name',
        required=True,
        help="Variant differentiator (e.g. Odoo Brand, Pro Edition, White Label)",
    )
    price_adjustment = fields.Float(
        string='Price Adjustment',
        digits=(16, 2),
        default=0.0,
        help="Price delta added to the product sales price (+/-)",
    )
    effective_price = fields.Float(
        string='Effective Price',
        digits=(16, 2),
        compute='_compute_effective_price',
        store=True,
        help="Total sales price: base sales price + variant price adjustment",
    )

    @api.depends('product_id.sales_price', 'price_adjustment')
    def _compute_effective_price(self):
        for variant in self:
            base_price = variant.product_id.sales_price if variant.product_id else 0.0
            variant.effective_price = base_price + variant.price_adjustment

    @api.depends('name', 'product_id.name')
    def _compute_display_name(self):
        for variant in self:
            if variant.product_id:
                variant.display_name = f"{variant.product_id.name} ({variant.name})"
            else:
                variant.display_name = variant.name or ""

    @api.constrains('price_adjustment', 'product_id')
    def _check_variant_pricing(self):
        for variant in self:
            base_price = variant.product_id.sales_price if variant.product_id else 0.0
            if (base_price + variant.price_adjustment) < 0.0:
                raise ValidationError(_("The resulting price after variant adjustment cannot be negative."))
