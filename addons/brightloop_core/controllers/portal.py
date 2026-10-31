# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Customer Portal Controller
Owner: Member 1 (Platform Foundation, Authentication & Security Lead)

Provides:
1. Customer portal dashboard integration hooks.
2. Server-side validation for customer profile edits (email format, duplicate checks).
3. Integration placeholders for Members 2, 3, and 4 workstreams.
"""

import re
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class BrightloopCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add Brightloop integration flags and placeholders to portal home."""
        values = super()._prepare_home_portal_values(counters)
        values.update({
            'is_brightloop_customer': request.env.user.is_brightloop_customer,
            'portal_client_category_enable': True,
        })
        return values

    def details_form_validate(self, data, partner_creation=False):
        """
        Validate profile updates on /my/account:
        - Enforce valid email syntax.
        - Prevent collisions with emails of existing accounts.
        """
        error, error_message = super().details_form_validate(data, partner_creation=partner_creation)

        email = data.get('email')
        if email:
            email = email.strip()
            if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
                error['email'] = 'error'
                error_message.append(_("Please provide a valid email address."))
            else:
                current_user_id = request.env.user.id
                existing = request.env['res.users'].sudo().search([
                    ('login', '=', email),
                    ('id', '!=', current_user_id),
                ], limit=1)
                if not existing:
                    existing = request.env['res.users'].sudo().search([
                        ('email', '=', email),
                        ('id', '!=', current_user_id),
                    ], limit=1)
                if existing:
                    error['email'] = 'error'
                    error_message.append(_("Another user is already registered using this email address."))

        return error, error_message

    # =========================================================================
    # Integration Placeholders for Members 2, 3, and 4
    # =========================================================================

    @http.route(['/my/subscriptions'], type='http', auth='user', website=True)
    def brightloop_portal_subscriptions(self, **kw):
        """Integration placeholder for Member 2 (brightloop_subscription)."""
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'subscriptions_placeholder',
            'workstream_member': 'Member 2',
            'workstream_addon': 'brightloop_subscription',
            'title': _('My Subscriptions'),
            'description': _('Subscription lifecycle, active plans, and renewals will be connected here by Member 2.'),
        })
        return request.render('brightloop_core.portal_integration_placeholder', values)

    @http.route(['/my/quotations'], type='http', auth='user', website=True)
    def brightloop_portal_quotations(self, **kw):
        """Integration placeholder for Member 2 (brightloop_subscription)."""
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'quotations_placeholder',
            'workstream_member': 'Member 2',
            'workstream_addon': 'brightloop_subscription',
            'title': _('My Quotations'),
            'description': _('Subscription quotations, pricing options, and plan approvals will be connected here by Member 2.'),
        })
        return request.render('brightloop_core.portal_integration_placeholder', values)

    @http.route(['/my/invoices'], type='http', auth='user', website=True)
    def brightloop_portal_invoices(self, **kw):
        """Integration placeholder for Member 3 (brightloop_billing)."""
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'invoices_placeholder',
            'workstream_member': 'Member 3',
            'workstream_addon': 'brightloop_billing',
            'title': _('My Invoices'),
            'description': _('Recurring billing statements, tax breakdowns, and invoices will be connected here by Member 3.'),
        })
        return request.render('brightloop_core.portal_integration_placeholder', values)

    @http.route(['/my/payments'], type='http', auth='user', website=True)
    def brightloop_portal_payments(self, **kw):
        """Integration placeholder for Member 4 (brightloop_finance)."""
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'payments_placeholder',
            'workstream_member': 'Member 4',
            'workstream_addon': 'brightloop_finance',
            'title': _('My Payments'),
            'description': _('Payment records, transaction receipts, and payment method summaries will be connected here by Member 4.'),
        })
        return request.render('brightloop_core.portal_integration_placeholder', values)
