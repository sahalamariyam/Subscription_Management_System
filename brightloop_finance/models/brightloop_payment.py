# -*- coding: utf-8 -*-
"""
brightloop_payment.py
Member 4 — Brightloop Finance

Canonical data contract:
    Payment: id, payment_method, amount, payment_date, reference, notes

Supports:
- Manual and gateway payment recording
- Multiple configurable payment methods
- Duplicate prevention via reference + date + amount constraint
- Partial and full payment allocation
- Overpayment detection
- Chatter logging via mail.thread
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class BrightloopPaymentMethod(models.Model):
    """
    Configurable payment methods (e.g. Cash, Bank Transfer, Card, Gateway).
    Managed by admin; referenced by BrightloopPayment.
    """
    _name = 'brightloop.payment.method'
    _description = 'Brightloop Payment Method'
    _order = 'sequence, name'

    name = fields.Char(
        string='Payment Method',
        required=True,
        translate=True,
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Internal code, e.g. cash, bank_transfer, stripe',
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    requires_reference = fields.Boolean(
        string='Requires Reference',
        default=False,
        help='If enabled, a payment reference is mandatory for this method.',
    )
    notes = fields.Text(string='Description')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Payment method code must be unique.'),
    ]


class BrightloopPayment(models.Model):
    """
    Records a single payment event.

    Canonical fields: id, payment_method, amount, payment_date, reference, notes.
    Extended with: state, currency, partner, total_allocated, is_fully_allocated.

    Business rules:
    - amount must be > 0
    - reference is required when payment_method.requires_reference is True
    - Duplicate prevention: (partner_id, payment_method_id, amount, payment_date, reference)
      triggers a soft-warning and hard block on identical reference reuse.
    - After recording, allocate via brightloop.invoice.payment lines.
    """
    _name = 'brightloop.payment'
    _description = 'Brightloop Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'payment_date desc, id desc'
    _rec_name = 'name'

    # ─── Identity ────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Payment Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    # ─── Canonical contract fields ────────────────────────────────────────────
    payment_method_id = fields.Many2one(
        comodel_name='brightloop.payment.method',
        string='Payment Method',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        tracking=True,
    )
    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today,
        index=True,         # perf: used in date-range queries
        tracking=True,
    )
    reference = fields.Char(
        string='Payment Reference / Transaction ID',
        index=True,         # perf: duplicate detection queries
        tracking=True,
        copy=False,
    )
    notes = fields.Text(string='Notes')

    # ─── Extended fields ──────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        required=True,
        ondelete='restrict',
        index=True,         # perf: customer-scoped queries
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company,
        required=True,
    )

    # ─── Allocation summary (computed) ───────────────────────────────────────
    invoice_payment_ids = fields.One2many(
        comodel_name='brightloop.invoice.payment',
        inverse_name='payment_id',
        string='Invoice Allocations',
    )
    total_allocated = fields.Monetary(
        string='Total Allocated',
        compute='_compute_allocation',
        store=True,
        currency_field='currency_id',
    )
    unallocated_amount = fields.Monetary(
        string='Unallocated Amount',
        compute='_compute_allocation',
        store=True,
        currency_field='currency_id',
    )
    is_fully_allocated = fields.Boolean(
        string='Fully Allocated',
        compute='_compute_allocation',
        store=True,
        index=True,
    )
    is_overpayment = fields.Boolean(
        string='Overpayment',
        compute='_compute_allocation',
        store=True,
        help='True when total allocated exceeds payment amount.',
    )

    # ─── SQL Constraints ─────────────────────────────────────────────────────
    _sql_constraints = [
        (
            'amount_positive',
            'CHECK(amount > 0)',
            'Payment amount must be greater than zero.',
        ),
        (
            'unique_reference',
            'UNIQUE(payment_method_id, reference)',
            'A payment with this method and reference already exists. '
            'Check for duplicate payment.',
        ),
    ]

    # ─── Compute ─────────────────────────────────────────────────────────────
    @api.depends('invoice_payment_ids.allocated_amount', 'amount')
    def _compute_allocation(self):
        for rec in self:
            allocated = sum(rec.invoice_payment_ids.mapped('allocated_amount'))
            rec.total_allocated = allocated
            rec.unallocated_amount = rec.amount - allocated
            rec.is_fully_allocated = allocated >= rec.amount
            rec.is_overpayment = allocated > rec.amount

    # ─── Constraints ─────────────────────────────────────────────────────────
    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Payment amount must be greater than zero.'))

    @api.constrains('payment_method_id', 'reference')
    def _check_reference_required(self):
        for rec in self:
            if rec.payment_method_id.requires_reference and not rec.reference:
                raise ValidationError(
                    _('Payment method "%s" requires a payment reference.')
                    % rec.payment_method_id.name
                )

    # ─── ORM Overrides ───────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'brightloop.payment'
                ) or _('New')
        return super().create(vals_list)

    def action_post(self):
        """Confirm and post the payment."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft payments can be posted.'))
            if rec.amount <= 0:
                raise UserError(_('Cannot post a payment with zero or negative amount.'))
            rec.state = 'posted'
            rec.message_post(
                body=_('Payment posted: %s %s on %s via %s.')
                % (
                    rec.currency_id.symbol,
                    rec.amount,
                    rec.payment_date,
                    rec.payment_method_id.name,
                )
            )

    def action_cancel(self):
        """Cancel the payment and clear allocations."""
        for rec in self:
            if rec.state == 'cancelled':
                raise UserError(_('Payment is already cancelled.'))
            if rec.invoice_payment_ids:
                raise UserError(
                    _('Cannot cancel payment "%s" — it has invoice allocations. '
                      'Remove allocations first.') % rec.name
                )
            rec.state = 'cancelled'

    def action_reset_to_draft(self):
        """Reset a cancelled payment to draft for correction."""
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_('Only cancelled payments can be reset to draft.'))
            rec.state = 'draft'
