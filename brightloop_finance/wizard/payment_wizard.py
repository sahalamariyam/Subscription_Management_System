# -*- coding: utf-8 -*-
"""
payment_wizard.py
Member 4 — Brightloop Finance

Guided payment recording wizard:
1. Select customer
2. Choose payment method and enter amount/reference
3. Select invoices to allocate against (with outstanding balance display)
4. Confirm — creates Payment + InvoicePayment allocation records atomically.

Prevents:
- Recording zero/negative payments
- Over-allocating against invoice balance
- Duplicate reference for the same payment method
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

INVOICE_MODEL = 'brightloop.invoice'


class PaymentWizardAllocationLine(models.TransientModel):
    """Transient allocation line inside the payment wizard."""
    _name = 'brightloop.payment.wizard.line'
    _description = 'Payment Wizard Allocation Line'

    wizard_id = fields.Many2one('brightloop.payment.wizard', required=True, ondelete='cascade')
    invoice_id = fields.Many2one(INVOICE_MODEL, string='Invoice', required=True)
    invoice_number = fields.Char(related='invoice_id.invoice_number', readonly=True)
    invoice_total = fields.Monetary(related='invoice_id.total', readonly=True,
                                     currency_field='currency_id')
    balance_due = fields.Monetary(related='invoice_id.balance_due', readonly=True,
                                   currency_field='currency_id')
    due_date = fields.Date(related='invoice_id.due_date', readonly=True)
    allocated_amount = fields.Monetary(string='Allocate', currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.currency_id', readonly=True)


class PaymentWizard(models.TransientModel):
    """
    Transient payment recording wizard.
    Provides guided UI for creating a Payment and its InvoicePayment allocations.
    """
    _name = 'brightloop.payment.wizard'
    _description = 'Record Payment Wizard'

    # ─── Step 1: Payment details ──────────────────────────────────────────────
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        required=True,
        domain=[('customer_rank', '>', 0)],
    )
    payment_method_id = fields.Many2one(
        comodel_name='brightloop.payment.method',
        string='Payment Method',
        required=True,
        domain=[('active', '=', True)],
    )
    amount = fields.Monetary(
        string='Payment Amount',
        required=True,
        currency_field='currency_id',
    )
    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today,
    )
    reference = fields.Char(string='Reference / Transaction ID')
    notes = fields.Text(string='Notes')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ─── Step 2: Allocation ───────────────────────────────────────────────────
    allocation_ids = fields.One2many(
        comodel_name='brightloop.payment.wizard.line',
        inverse_name='wizard_id',
        string='Allocate to Invoices',
    )
    total_allocated = fields.Monetary(
        string='Total Allocated',
        compute='_compute_totals',
        currency_field='currency_id',
    )
    remaining = fields.Monetary(
        string='Remaining / Unallocated',
        compute='_compute_totals',
        currency_field='currency_id',
    )

    @api.depends('allocation_ids.allocated_amount', 'amount')
    def _compute_totals(self):
        for rec in self:
            total = sum(rec.allocation_ids.mapped('allocated_amount'))
            rec.total_allocated = total
            rec.remaining = rec.amount - total

    @api.onchange('partner_id')
    def _onchange_partner(self):
        """Auto-load outstanding invoices for the selected customer."""
        self.allocation_ids = [(5, 0, 0)]
        if self.partner_id and INVOICE_MODEL in self.env:
            open_invoices = self.env[INVOICE_MODEL].search([
                ('partner_id', '=', self.partner_id.id),
                ('balance_due', '>', 0),
                ('status', 'not in', ['cancelled', 'draft', 'paid']),
            ], order='due_date asc', limit=20)
            self.allocation_ids = [
                (0, 0, {
                    'invoice_id': inv.id,
                    'allocated_amount': 0.0,
                })
                for inv in open_invoices
            ]

    def action_confirm(self):
        """
        Create Payment and InvoicePayment allocation records atomically.
        Validates all amounts before writing.
        """
        self.ensure_one()

        if self.amount <= 0:
            raise ValidationError(_('Payment amount must be greater than zero.'))

        if self.remaining < -1e-9:
            raise ValidationError(
                _('Total allocated (%(alloc)s) exceeds payment amount (%(amt)s). '
                  'Reduce allocations before confirming.') % {
                    'alloc': self.total_allocated,
                    'amt': self.amount,
                }
            )

        # Validate each allocation line
        for line in self.allocation_ids:
            if line.allocated_amount < 0:
                raise ValidationError(
                    _('Allocated amount cannot be negative for invoice %s.')
                    % line.invoice_number
                )
            if line.allocated_amount > line.balance_due + 1e-9:
                raise ValidationError(
                    _('Allocated amount (%(alloc)s) exceeds outstanding balance '
                      '(%(bal)s) for invoice %(inv)s.') % {
                        'alloc': line.allocated_amount,
                        'bal': line.balance_due,
                        'inv': line.invoice_number,
                    }
                )

        # Create payment
        payment = self.env['brightloop.payment'].create({
            'partner_id': self.partner_id.id,
            'payment_method_id': self.payment_method_id.id,
            'amount': self.amount,
            'payment_date': self.payment_date,
            'reference': self.reference,
            'notes': self.notes,
            'currency_id': self.currency_id.id,
        })

        # Post immediately
        payment.action_post()

        # Create allocation lines (only for non-zero amounts)
        allocation_lines = [
            line for line in self.allocation_ids if line.allocated_amount > 0
        ]
        for line in allocation_lines:
            self.env['brightloop.invoice.payment'].create({
                'payment_id': payment.id,
                'invoice_id': line.invoice_id.id,
                'allocated_amount': line.allocated_amount,
            })

        # Return to the created payment record
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment'),
            'res_model': 'brightloop.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'current',
        }
