# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Quotation Template Models
Owner: Member 2 (Product, Plan, Quotation & Subscription Lifecycle Lead)

Implements:
- Reusable quotation templates for sales representatives.
- Template product lines with predefined quantities, unit prices, and tax references.
- Association with default subscription plans and validity durations.
- One-click customer quotation instantiation from templates.
"""

from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class BrightloopQuotationTemplate(models.Model):
    _name = 'brightloop.quotation.template'
    _description = 'Brightloop Quotation Template'
    _order = 'name asc'

    name = fields.Char(
        string='Template Name',
        required=True,
        help="Name of the standard sales offer (e.g. Starter Pack, Growth Tier)",
    )
    plan_id = fields.Many2one(
        'brightloop.plan',
        string='Subscription Plan',
        required=True,
        help="Default recurring billing plan for this quotation template",
    )
    validity_days = fields.Integer(
        string='Quotation Validity (Days)',
        default=30,
        required=True,
        help="Number of days quotations generated from this template remain valid before expiry",
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    line_ids = fields.One2many(
        'brightloop.quotation.template.line',
        'template_id',
        string='Template Lines',
        help="Predefined products, variants, and quantities included in this offer",
    )

    @api.constrains('validity_days')
    def _check_validity_days(self):
        for template in self:
            if template.validity_days < 1:
                raise ValidationError(_("Quotation validity period must be at least 1 day."))

    def action_generate_quotation_for_customer(self, partner_id):
        """
        Create a new brightloop.subscription in quotation status for the customer,
        pre-populated with template plan, validity, and product lines.
        """
        self.ensure_one()
        if not partner_id:
            raise UserError(_("A customer partner must be specified to generate a quotation."))

        partner = self.env['res.partner'].browse(partner_id)
        if not partner.exists():
            raise UserError(_("Customer partner does not exist."))

        today = fields.Date.today()
        valid_until = today + relativedelta(days=self.validity_days)

        subscription_lines = []
        for line in self.line_ids:
            subscription_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'variant_id': line.variant_id.id if line.variant_id else False,
                'name': line.name or line.product_id.name,
                'quantity': line.quantity,
                'unit_price': line.unit_price,
                'tax_id': line.tax_id,
            }))

        subscription_vals = {
            'partner_id': partner.id,
            'plan_id': self.plan_id.id,
            'template_id': self.id,
            'status': 'draft',
            'valid_until': valid_until,
            'line_ids': subscription_lines,
        }
        subscription = self.env['brightloop.subscription'].create(subscription_vals)
        # Advance to quotation status
        subscription.action_send_quotation()
        return subscription


class BrightloopQuotationTemplateLine(models.Model):
    _name = 'brightloop.quotation.template.line'
    _description = 'Brightloop Quotation Template Line'
    _order = 'id asc'

    template_id = fields.Many2one(
        'brightloop.quotation.template',
        string='Quotation Template',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_id = fields.Many2one(
        'brightloop.product',
        string='Product',
        required=True,
    )
    variant_id = fields.Many2one(
        'brightloop.product.variant',
        string='Product Variant',
        domain="[('product_id', '=', product_id)]",
    )
    name = fields.Char(
        string='Description',
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
    )
    unit_price = fields.Float(
        string='Unit Price',
        digits=(16, 2),
        required=True,
        default=0.0,
    )
    tax_id = fields.Char(
        string='Tax Reference',
        help="Tax specification code or rate for Member 3 billing engine (e.g. GST_18)",
    )

    @api.onchange('product_id', 'variant_id')
    def _onchange_product(self):
        if self.variant_id and self.variant_id.product_id == self.product_id:
            self.unit_price = self.variant_id.effective_price
            self.name = self.variant_id.display_name
        elif self.product_id:
            self.unit_price = self.product_id.sales_price
            self.name = self.product_id.name

    @api.constrains('quantity', 'unit_price')
    def _check_line_values(self):
        for line in self:
            if line.quantity <= 0.0:
                raise ValidationError(_("Line quantity must be strictly positive."))
            if line.unit_price < 0.0:
                raise ValidationError(_("Unit price cannot be negative."))
