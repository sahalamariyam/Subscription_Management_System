# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Customer Portal Controller
Owner: Member 1 (Platform Foundation, Authentication & Security Lead)

Provides:
1. Customer portal home integration — subscription/invoice/payment counters.
2. Live portal pages for:
   - /my/subscriptions  — brightloop.subscription records (Member 2)
   - /my/quotations     — draft/quotation subscriptions (Member 2)
   - /my/invoices       — account.move invoices (Member 3)
   - /my/payments       — brightloop.payment records (Member 4)
3. Server-side validation for customer profile edits (email format, duplicate checks).
"""

import re
from datetime import date as _date
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


# ── Pagination page size ──────────────────────────────────────────────────────
_PAGE_SIZE = 10


class BrightloopCustomerPortal(CustomerPortal):

    # =========================================================================
    # Portal Home — counters sidebar
    # =========================================================================

    def _prepare_home_portal_values(self, counters):
        """Add Brightloop counters and integration flags to portal home."""
        values = super()._prepare_home_portal_values(counters)

        user = request.env.user
        partner = user.partner_id

        if 'subscription_count' in counters:
            values['subscription_count'] = request.env['brightloop.subscription'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('status', 'in', ['active', 'confirmed']),
            ]) if 'brightloop.subscription' in request.env else 0

        if 'invoice_count' in counters:
            values['invoice_count'] = request.env['account.move'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ]) if 'account.move' in request.env else 0

        if 'payment_count' in counters:
            values['payment_count'] = request.env['brightloop.payment'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('state', '=', 'posted'),
            ]) if 'brightloop.payment' in request.env else 0

        values.update({
            'is_brightloop_customer': user.is_brightloop_customer,
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
            if not re.match(r'^[^\@\s]+@[^\@\s]+\.[^\@\s]+$', email):
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
    # /my/subscriptions  (Member 2 — brightloop_subscription)
    # =========================================================================

    @http.route(['/my/subscriptions', '/my/subscriptions/page/<int:page>'],
                type='http', auth='user', website=True)
    def brightloop_portal_subscriptions(self, page=1, sortby=None, filterby=None, **kw):
        """Live subscription portal — active and confirmed subscriptions."""
        partner = request.env.user.partner_id

        # Sort options
        sort_options = {
            'date_desc': {'label': 'Newest First',    'order': 'create_date desc'},
            'date_asc':  {'label': 'Oldest First',    'order': 'create_date asc'},
            'name':      {'label': 'Name',             'order': 'name asc'},
        }
        sortby = sortby or 'date_desc'
        order = sort_options.get(sortby, sort_options['date_desc'])['order']

        # Filter options
        filter_options = {
            'all':    {'label': 'All Active',  'domain': [('status', 'in', ['active', 'confirmed'])]},
            'active': {'label': 'Running',     'domain': [('status', '=', 'active'), ('is_paused', '=', False)]},
            'paused': {'label': 'Paused',      'domain': [('status', '=', 'active'), ('is_paused', '=', True)]},
        }
        filterby = filterby or 'all'
        filter_domain = filter_options.get(filterby, filter_options['all'])['domain']

        # Model availability guard
        if 'brightloop.subscription' not in request.env:
            values = self._prepare_portal_layout_values()
            values.update({
                'page_name': 'subscriptions',
                'subscriptions': [],
                'pager': {},
                'sort_options': sort_options,
                'filter_options': filter_options,
                'sortby': sortby,
                'filterby': filterby,
                'module_unavailable': True,
            })
            return request.render('brightloop_core.portal_subscriptions', values)

        domain = [('partner_id', '=', partner.id)] + filter_domain
        Sub = request.env['brightloop.subscription'].sudo()

        total = Sub.search_count(domain)
        pager = portal_pager(
            url='/my/subscriptions',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=total,
            page=page,
            step=_PAGE_SIZE,
        )
        subscriptions = Sub.search(domain, order=order,
                                   limit=_PAGE_SIZE, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'subscriptions',
            'subscriptions': subscriptions,
            'pager': pager,
            'sort_options': sort_options,
            'filter_options': filter_options,
            'sortby': sortby,
            'filterby': filterby,
            'module_unavailable': False,
        })
        return request.render('brightloop_core.portal_subscriptions', values)

    @http.route(['/my/subscriptions/<int:sub_id>'],
                type='http', auth='user', website=True)
    def brightloop_portal_subscription_detail(self, sub_id, **kw):
        """Single subscription detail page."""
        partner = request.env.user.partner_id
        if 'brightloop.subscription' not in request.env:
            return request.redirect('/my/subscriptions')

        sub = request.env['brightloop.subscription'].sudo().browse(sub_id)
        if not sub.exists() or sub.partner_id.id != partner.id:
            return request.redirect('/my/subscriptions')

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'subscriptions',
            'subscription': sub,
        })
        return request.render('brightloop_core.portal_subscription_detail', values)

    # =========================================================================
    # /my/quotations  (Member 2 — draft/quotation subscriptions)
    # =========================================================================

    @http.route(['/my/quotations', '/my/quotations/page/<int:page>'],
                type='http', auth='user', website=True)
    def brightloop_portal_quotations(self, page=1, **kw):
        """Live quotations portal — draft and quotation-stage subscriptions."""
        partner = request.env.user.partner_id

        if 'brightloop.subscription' not in request.env:
            values = self._prepare_portal_layout_values()
            values.update({
                'page_name': 'quotations',
                'subscriptions': [],
                'pager': {},
                'module_unavailable': True,
            })
            return request.render('brightloop_core.portal_quotations', values)

        domain = [
            ('partner_id', '=', partner.id),
            ('status', 'in', ['draft', 'quotation']),
        ]
        Sub = request.env['brightloop.subscription'].sudo()
        total = Sub.search_count(domain)
        pager = portal_pager(
            url='/my/quotations',
            total=total,
            page=page,
            step=_PAGE_SIZE,
        )
        subscriptions = Sub.search(domain, order='create_date desc',
                                   limit=_PAGE_SIZE, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'quotations',
            'subscriptions': subscriptions,
            'pager': pager,
            'module_unavailable': False,
        })
        return request.render('brightloop_core.portal_quotations', values)

    # =========================================================================
    # /my/invoices  (Member 3 — account.move)
    # =========================================================================

    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'],
                type='http', auth='user', website=True)
    def brightloop_portal_invoices(self, page=1, filterby=None, **kw):
        """Live invoices portal — posted customer invoices."""
        partner = request.env.user.partner_id

        filter_options = {
            'all':     {'label': 'All',        'domain': []},
            'unpaid':  {'label': 'Unpaid',     'domain': [('payment_state', 'not in', ['paid', 'reversed'])]},
            'paid':    {'label': 'Paid',       'domain': [('payment_state', '=', 'paid')]},
            'overdue': {'label': 'Overdue',    'domain': [
                ('payment_state', 'not in', ['paid', 'reversed']),
                ('invoice_date_due', '<', str(_date.today())),
            ]},
        }
        filterby = filterby or 'all'
        filter_domain = filter_options.get(filterby, filter_options['all'])['domain']

        base_domain = [
            ('partner_id', '=', partner.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ] + filter_domain

        # Guard: account module may not be installed in isolated test environments
        if 'account.move' not in request.env:
            values = self._prepare_portal_layout_values()
            values.update({
                'page_name': 'invoices',
                'invoices': [],
                'pager': {},
                'filter_options': filter_options,
                'filterby': filterby,
            })
            return request.render('brightloop_core.portal_invoices', values)

        Inv = request.env['account.move'].sudo()
        total = Inv.search_count(base_domain)
        pager = portal_pager(
            url='/my/invoices',
            url_args={'filterby': filterby},
            total=total,
            page=page,
            step=_PAGE_SIZE,
        )
        invoices = Inv.search(base_domain, order='invoice_date desc',
                              limit=_PAGE_SIZE, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'invoices',
            'invoices': invoices,
            'pager': pager,
            'filter_options': filter_options,
            'filterby': filterby,
        })
        return request.render('brightloop_core.portal_invoices', values)

    @http.route(['/my/invoices/<int:invoice_id>'],
                type='http', auth='user', website=True)
    def brightloop_portal_invoice_detail(self, invoice_id, **kw):
        """Single invoice detail page."""
        partner = request.env.user.partner_id
        if 'account.move' not in request.env:
            return request.redirect('/my/invoices')
        invoice = request.env['account.move'].sudo().browse(invoice_id)
        if (not invoice.exists()
                or invoice.partner_id.id != partner.id
                or invoice.move_type != 'out_invoice'):
            return request.redirect('/my/invoices')

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'invoices',
            'invoice': invoice,
        })
        return request.render('brightloop_core.portal_invoice_detail', values)

    # =========================================================================
    # /my/payments  (Member 4 — brightloop_finance)
    # =========================================================================

    @http.route(['/my/payments', '/my/payments/page/<int:page>'],
                type='http', auth='user', website=True)
    def brightloop_portal_payments(self, page=1, **kw):
        """Live payments portal — posted brightloop.payment records."""
        partner = request.env.user.partner_id

        if 'brightloop.payment' not in request.env:
            values = self._prepare_portal_layout_values()
            values.update({
                'page_name': 'payments',
                'payments': [],
                'pager': {},
                'module_unavailable': True,
            })
            return request.render('brightloop_core.portal_payments', values)

        domain = [
            ('partner_id', '=', partner.id),
            ('state', '=', 'posted'),
        ]
        Pay = request.env['brightloop.payment'].sudo()
        total = Pay.search_count(domain)
        pager = portal_pager(
            url='/my/payments',
            total=total,
            page=page,
            step=_PAGE_SIZE,
        )
        payments = Pay.search(domain, order='payment_date desc',
                              limit=_PAGE_SIZE, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'payments',
            'payments': payments,
            'pager': pager,
            'module_unavailable': False,
        })
        return request.render('brightloop_core.portal_payments', values)
