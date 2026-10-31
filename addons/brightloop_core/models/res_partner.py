# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Customer & Contact Model Extensions
Owner: Member 1 (Platform Foundation, Authentication & Security Lead)

Establishes canonical customer-partner identity conventions:
- Links customer login (res.users) to customer profile (res.partner).
- Provides helpers for customer data isolation.
- Prepares integration contracts for subscription, billing, and finance modules.
"""

from odoo import api, fields, models
from .shared_constants import ROLE_CUSTOMER, ROLE_SELECTION


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_user_id = fields.Many2one(
        'res.users',
        string='Customer User Account',
        compute='_compute_customer_user',
        store=False,
        help="Primary login account associated with this customer",
    )

    is_brightloop_customer = fields.Boolean(
        string='Is Brightloop Customer',
        compute='_compute_customer_user',
        store=False,
        help="True if this partner is linked to an active Brightloop Customer portal user",
    )

    brightloop_role = fields.Selection(
        selection=ROLE_SELECTION,
        string='Brightloop Identity Role',
        compute='_compute_customer_user',
        store=False,
        help="Canonical role of the associated login user",
    )

    @api.depends('user_ids', 'user_ids.groups_id')
    def _compute_customer_user(self):
        customer_group = self.env.ref('brightloop_core.group_brightloop_customer', raise_if_not_found=False)

        for partner in self:
            primary_user = partner.user_ids[:1]
            partner.customer_user_id = primary_user.id if primary_user else False

            if primary_user:
                partner.brightloop_role = primary_user.brightloop_role
                if customer_group and customer_group in primary_user.groups_id:
                    partner.is_brightloop_customer = True
                else:
                    partner.is_brightloop_customer = bool(primary_user.share)
            else:
                partner.brightloop_role = False
                partner.is_brightloop_customer = False
