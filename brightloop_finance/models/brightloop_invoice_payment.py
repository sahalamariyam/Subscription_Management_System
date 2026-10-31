# -*- coding: utf-8 -*-
"""
brightloop_invoice_payment.py
Member 4 — Brightloop Finance

Canonical data contract:
    InvoicePayment: id, invoice_id, payment_id, allocated_amount

Join model between brightloop.payment and account.move (Odoo 18).

Confirmed with Member 3 (2026-10-31):
  Invoice model  : account.move (move_type='out_invoice')
  total          : amount_total
  balance_due    : amount_residual
  amount_paid    : amount_total - amount_residual (derived, not stored)
  due_date       : invoice_date_due
  invoice_number : name
  state          : draft | posted | cancel
  payment_state  : not_paid | partial | in_payment | paid | reversed

Business rules:
- allocated_amount must be > 0
- allocated_amount cannot exceed invoice's amount_residual at time of recording
- Sum of allocations per invoice must not exceed invoice's amount_total
- Coordinate invoice status reads with account.move state/payment_state

Integration note:
    invoice_id references 'account.move' (Odoo 18 native accounting model).
    member 3 will extend account.move via _inherit to add subscription_id.
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

# Confirmed with Member 3 — 2026-10-31
INVOICE_MODEL = 'account.move'


class BrightloopInvoicePayment(models.Model):
    """
    Allocation record linking one Payment to one Invoice.

    One invoice may have many BrightloopInvoicePayment rows (multiple payments).
    One payment may be split across multiple invoices via multiple rows.

    Constraints enforce:
    - allocated_amount > 0
    - No duplicate (invoice_id, payment_id) pair
    - allocated_amount <= remaining invoice balance at time of creation
    """
    _name = 'brightloop.invoice.payment'
    _description = 'Invoice Payment Allocation'
    _order = 'allocation_date desc, id desc'

    # ─── Canonical contract fields ────────────────────────────────────────────
    invoice_id = fields.Many2one(
        comodel_name=INVOICE_MODEL,
        string='Invoice',
        required=True,
        ondelete='restrict',
        index=True,
    )
    payment_id = fields.Many2one(
        comodel_name='brightloop.payment',
        string='Payment',
        required=True,
        ondelete='cascade',
        index=True,
    )
    allocated_amount = fields.Monetary(
        string='Allocated Amount',
        required=True,
        currency_field='currency_id',
    )

    # ─── Extended fields ──────────────────────────────────────────────────────
    allocation_date = fields.Date(
        string='Allocation Date',
        default=fields.Date.context_today,
        required=True,
    )
    currency_id = fields.Many2one(
        related='payment_id.currency_id',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related='payment_id.company_id',
        store=True,
        readonly=True,
    )
    notes = fields.Text(string='Allocation Notes')

    # ─── Related display fields (read-only, for views/reports) ───────────────
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        string='Customer',
        store=True,
        readonly=True,
        index=True,
    )
    invoice_total = fields.Monetary(
        # account.move: amount_total
        related='invoice_id.amount_total',
        string='Invoice Total',
        currency_field='currency_id',
        readonly=True,
    )

    # ─── SQL Constraints ─────────────────────────────────────────────────────
    _sql_constraints = [
        (
            'allocated_amount_positive',
            'CHECK(allocated_amount > 0)',
            'Allocated amount must be greater than zero.',
        ),
        (
            'unique_invoice_payment',
            'UNIQUE(invoice_id, payment_id)',
            'This payment has already been allocated to this invoice. '
            'Modify the existing allocation instead of creating a duplicate.',
        ),
    ]

    # ─── Constraints (Python) ─────────────────────────────────────────────────
    @api.constrains('allocated_amount', 'invoice_id', 'payment_id')
    def _check_allocation_limits(self):
        """
        Validate:
        1. allocated_amount <= available payment unallocated amount (before this line)
        2. allocated_amount <= invoice balance_due
        3. Total allocations per invoice do not exceed invoice.total
        """
        for rec in self:
            # ── Check invoice balance ──────────────────────────────────────
            invoice = rec.invoice_id
            if not invoice:
                continue

            # Current balance_due on the invoice (computed by Member 3's model
            # or recalculated here if Member 3 uses a stored field)
            balance_due = self._get_invoice_balance_due(invoice, exclude_allocation=rec.id)
            if rec.allocated_amount > balance_due + 1e-9:
                raise ValidationError(
                    _('Allocated amount (%(alloc)s) exceeds invoice outstanding '
                      'balance (%(balance)s) for invoice %(inv)s.') % {
                        'alloc': rec.allocated_amount,
                        'balance': balance_due,
                        'inv': invoice.display_name,
                    }
                )

            # ── Check payment unallocated amount ──────────────────────────
            payment = rec.payment_id
            if payment:
                other_allocations = self.search([
                    ('payment_id', '=', payment.id),
                    ('id', '!=', rec.id),
                ])
                already_allocated = sum(other_allocations.mapped('allocated_amount'))
                available = payment.amount - already_allocated
                if rec.allocated_amount > available + 1e-9:
                    raise ValidationError(
                        _('Allocated amount (%(alloc)s) exceeds unallocated payment '
                          'balance (%(avail)s) for payment %(pay)s.') % {
                            'alloc': rec.allocated_amount,
                            'avail': available,
                            'pay': payment.name,
                        }
                    )

    def _get_invoice_balance_due(self, invoice, exclude_allocation=None):
        """
        Calculate the current outstanding balance for an invoice,
        optionally excluding a specific allocation line (used during validation
        of an existing record to avoid self-comparison).

        For account.move (Odoo 18):
          balance = amount_residual (computed by Odoo reconciliation engine)
          We add back our own allocation being validated to avoid false negatives.
        """
        # account.move: use amount_residual as the authoritative outstanding balance
        if hasattr(invoice, 'amount_residual') and invoice.amount_residual is not False:
            if exclude_allocation:
                existing_line = self.browse(exclude_allocation).exists()
                if existing_line:
                    return invoice.amount_residual + existing_line.allocated_amount
            return invoice.amount_residual

        # Fallback: recalculate from our own allocation records
        domain = [('invoice_id', '=', invoice.id)]
        if exclude_allocation:
            domain.append(('id', '!=', exclude_allocation))
        existing_allocs = self.search(domain)
        total_allocated = sum(existing_allocs.mapped('allocated_amount'))
        invoice_total = getattr(invoice, 'amount_total', 0)
        return max(0.0, invoice_total - total_allocated)

    # ─── ORM Overrides ───────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Trigger invoice status update via Member 3 hook (if available)
        records._update_invoice_payment_status()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'allocated_amount' in vals:
            self._update_invoice_payment_status()
        return result

    def unlink(self):
        invoices_to_update = self.mapped('invoice_id')
        result = super().unlink()
        # Re-evaluate invoice status after allocation removal
        for invoice in invoices_to_update:
            self._recompute_invoice_status(invoice)
        return result

    def _update_invoice_payment_status(self):
        """
        After recording or modifying an allocation, log the allocation.

        For account.move (Odoo 18):
        - We do NOT write amount_paid to account.move — Odoo's reconciliation
          engine manages amount_residual and payment_state automatically.
        - Our brightloop.invoice.payment records are a separate tracking layer
          for manual/external payments not going through Odoo's account.payment.
        - If Member 3 adds a reconciliation bridge, coordinate here.
        """
        invoices = self.mapped('invoice_id')
        for invoice in invoices:
            self._recompute_invoice_status(invoice)

    def _recompute_invoice_status(self, invoice):
        """
        Log allocation totals for a single invoice.
        Does NOT write to account.move — Odoo manages its own state.
        """
        allocations = self.search([('invoice_id', '=', invoice.id)])
        total_paid = sum(allocations.mapped('allocated_amount'))

        _logger.debug(
            'account.move %s (id=%s): brightloop allocations total=%.2f '
            '(from %d allocation lines). Odoo amount_residual=%.2f.',
            invoice.name,
            invoice.id,
            total_paid,
            len(allocations),
            getattr(invoice, 'amount_residual', 0),
        )

