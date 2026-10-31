# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BrightloopBillingJob(models.Model):
    _name = 'brightloop.billing.job'
    _description = 'Brightloop Recurring Billing Job'
    _order = 'create_date desc, id desc'
    _rec_name = 'idempotency_key'

    subscription_id = fields.Many2one(
        comodel_name='brightloop.subscription',
        string='Subscription',
        required=True,
        index=True,
        ondelete='restrict',
    )

    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Generated Invoice',
        readonly=True,
        copy=False,
        ondelete='restrict',
        domain=[('move_type', '=', 'out_invoice')],
    )

    billing_period_start = fields.Date(
        string='Billing Period Start',
        required=True,
        index=True,
    )

    billing_period_end = fields.Date(
        string='Billing Period End',
        required=True,
    )

    idempotency_key = fields.Char(
        string='Idempotency Key',
        required=True,
        readonly=True,
        copy=False,
        index=True,
    )

    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('done', 'Completed'),
            ('failed', 'Failed'),
        ],
        string='Status',
        default='pending',
        required=True,
        index=True,
    )

    attempted_at = fields.Datetime(
        string='Attempted At',
        readonly=True,
    )

    completed_at = fields.Datetime(
        string='Completed At',
        readonly=True,
    )

    error_message = fields.Text(
        string='Error Details',
        readonly=True,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='subscription_id.company_id',
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True,
    )

    amount_total = fields.Monetary(
        string='Invoice Total',
        related='invoice_id.amount_total',
        currency_field='currency_id',
        readonly=True,
    )

    _sql_constraints = [
        (
            'billing_job_idempotency_key_unique',
            'UNIQUE(idempotency_key)',
            'A billing job already exists for this billing cycle.',
        ),
    ]

    @api.constrains('billing_period_start', 'billing_period_end')
    def _check_billing_period(self):
        for job in self:
            if job.billing_period_end < job.billing_period_start:
                raise ValidationError(
                    _('Billing period end cannot be before its start date.')
                )

    def action_view_invoice(self):
        self.ensure_one()

        if not self.invoice_id:
            return False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }
