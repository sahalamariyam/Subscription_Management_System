# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    subscription_id = fields.Many2one(
        comodel_name='brightloop.subscription',
        string='Subscription',
        index=True,
        ondelete='restrict',
        copy=False,
        help='Subscription associated with this customer invoice.',
    )
