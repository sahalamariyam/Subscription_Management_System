# -*- coding: utf-8 -*-
"""
brightloop_finance_report.py
Member 4 — Brightloop Finance

Financial dashboard aggregation and reporting model.

Provides:
- Revenue received (only from posted payments with allocations)
- Outstanding balances (invoice.total - amount_paid where balance_due > 0)
- Overdue invoice identification (due_date < today AND balance_due > 0)
- Dashboard KPI aggregation with date filters
- Data for Excel export

Performance:
- Uses database-level aggregation (read_group) to avoid loading all records
- All filter fields are indexed
- Pagination supported via limit/offset on list methods

Integration contracts (confirmed):
  Member 2 (brightloop.subscription):
    _name       = 'brightloop.subscription'   ✅ confirmed
    customer_id = Many2one('res.partner')     ✅ confirmed (alias for partner_id)
    status      = Selection([
                    'draft', 'quotation', 'confirmed', 'active', 'closed'
                  ])                          ✅ confirmed
    is_paused   = Boolean                     ✅ confirmed (paused stay 'active')
    pause_date  = Date                        ✅ confirmed
    next_billing_date = Date                  ✅ confirmed, indexed

  Member 3 (brightloop.invoice):
    _name       = 'brightloop.invoice'        ⏳ pending confirmation
"""

from odoo import api, fields, models, _
from odoo.exceptions import AccessError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

# ── Integration constants — confirmed with Member 2 on 2026-10-31 ────────────
INVOICE_MODEL = 'brightloop.invoice'
SUBSCRIPTION_MODEL = 'brightloop.subscription'   # confirmed ✅

# Canonical subscription status values (Member 2 confirmed 2026-10-31)
SUB_STATUS_ACTIVE    = 'active'
SUB_STATUS_CLOSED    = 'closed'
SUB_STATUS_DRAFT     = 'draft'
SUB_STATUS_QUOTATION = 'quotation'
SUB_STATUS_CONFIRMED = 'confirmed'


class BrightloopFinanceDashboard(models.TransientModel):
    """
    Transient model used as a controller for dashboard data aggregation.

    Does NOT store data — reads from brightloop.payment,
    brightloop.invoice.payment, and Member 3/1 models.

    Usage: instantiate with date filters via the wizard or controller.
    """
    _name = 'brightloop.finance.dashboard'
    _description = 'Brightloop Financial Dashboard'

    date_from = fields.Date(string='From', default=lambda self: date.today().replace(day=1))
    date_to = fields.Date(string='To', default=fields.Date.context_today)

    # ─── Dashboard KPIs (computed on demand) ─────────────────────────────────
    active_subscription_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_kpis',
        help='Active and not paused (status=active, is_paused=False).',
    )
    paused_subscription_count = fields.Integer(
        string='Paused Subscriptions',
        compute='_compute_kpis',
        help='Subscriptions with status=active but is_paused=True.',
    )
    revenue_received = fields.Float(
        string='Revenue Received',
        compute='_compute_kpis',
        digits=(16, 2),
        help='Sum of allocated amounts from posted payments within the date range.',
    )
    total_outstanding = fields.Float(
        string='Total Outstanding',
        compute='_compute_kpis',
        digits=(16, 2),
        help='Sum of balance_due across all non-zero invoices.',
    )
    overdue_invoice_count = fields.Integer(
        string='Overdue Invoices',
        compute='_compute_kpis',
    )
    overdue_amount = fields.Float(
        string='Overdue Amount',
        compute='_compute_kpis',
        digits=(16, 2),
    )
    total_invoice_value = fields.Float(
        string='Total Invoiced',
        compute='_compute_kpis',
        digits=(16, 2),
    )

    @api.depends('date_from', 'date_to')
    def _compute_kpis(self):
        for rec in self:
            active, paused = rec._get_subscription_counts()
            rec.active_subscription_count = active
            rec.paused_subscription_count = paused
            revenue, total_outstanding, overdue_count, overdue_amount, total_invoice = (
                rec._get_financial_kpis()
            )
            rec.revenue_received = revenue
            rec.total_outstanding = total_outstanding
            rec.overdue_invoice_count = overdue_count
            rec.overdue_amount = overdue_amount
            rec.total_invoice_value = total_invoice

    def _get_subscription_counts(self):
        """
        Return (active_count, paused_count) from brightloop.subscription.

        Confirmed contract (Member 2, 2026-10-31):
        - Paused subscriptions retain status='active' with is_paused=True.
        - Active (running) = status='active' AND is_paused=False.
        - Paused            = status='active' AND is_paused=True.
        """
        if SUBSCRIPTION_MODEL not in self.env:
            _logger.warning('Subscription model %s not yet available.', SUBSCRIPTION_MODEL)
            return 0, 0

        Sub = self.env[SUBSCRIPTION_MODEL]
        active_count = Sub.search_count([
            ('status', '=', SUB_STATUS_ACTIVE),
            ('is_paused', '=', False),
        ])
        paused_count = Sub.search_count([
            ('status', '=', SUB_STATUS_ACTIVE),
            ('is_paused', '=', True),
        ])
        return active_count, paused_count

    def _get_financial_kpis(self):
        """
        Aggregate financial KPIs using database-level queries.
        Returns: (revenue_received, total_outstanding, overdue_count,
                  overdue_amount, total_invoice_value)

        Invoice status values: pending confirmation from Member 3.
        Using defensive 'not in cancelled/draft' until Member 3 confirms
        the full selection set.
        """
        today = date.today()
        date_from = self.date_from or date.today().replace(day=1)
        date_to = self.date_to or today

        # ── Revenue received (posted payments within date range) ──────────
        # Only allocations from posted payments count as collected revenue.
        payment_domain = [
            ('payment_id.state', '=', 'posted'),
            ('allocation_date', '>=', date_from),
            ('allocation_date', '<=', date_to),
        ]
        alloc_data = self.env['brightloop.invoice.payment'].read_group(
            domain=payment_domain,
            fields=['allocated_amount:sum'],
            groupby=[],
        )
        revenue = alloc_data[0]['allocated_amount'] if alloc_data else 0.0

        # ── Invoice aggregation (from Member 3's model) ───────────────────
        total_invoice_value = 0.0
        total_outstanding = 0.0
        overdue_count = 0
        overdue_amount = 0.0

        if INVOICE_MODEL in self.env:
            # Total invoice value (all confirmed/posted invoices in period)
            # TODO: update excluded statuses once Member 3 confirms selection values
            inv_domain = [
                ('status', 'not in', ['cancelled', 'draft']),
                ('invoice_date', '>=', str(date_from)),
                ('invoice_date', '<=', str(date_to)),
            ]
            inv_data = self.env[INVOICE_MODEL].read_group(
                domain=inv_domain,
                fields=['total:sum'],
                groupby=[],
            )
            total_invoice_value = inv_data[0]['total'] if inv_data else 0.0

            # Outstanding: balance_due > 0
            outstanding_domain = inv_domain + [('balance_due', '>', 0)]
            out_data = self.env[INVOICE_MODEL].read_group(
                domain=outstanding_domain,
                fields=['balance_due:sum'],
                groupby=[],
            )
            total_outstanding = out_data[0]['balance_due'] if out_data else 0.0

            # Overdue: due_date < today AND balance_due > 0
            # Not filtering by status='paid' since Member 3 hasn't confirmed
            # that 'paid' is a valid status — relying on balance_due > 0 instead.
            overdue_domain = [
                ('status', 'not in', ['cancelled', 'draft']),
                ('due_date', '<', str(today)),
                ('balance_due', '>', 0),
            ]
            overdue_data = self.env[INVOICE_MODEL].read_group(
                domain=overdue_domain,
                fields=['balance_due:sum', 'id:count'],
                groupby=[],
            )
            if overdue_data:
                overdue_count = overdue_data[0].get('id_count', 0) or overdue_data[0].get('__count', 0)
                overdue_amount = overdue_data[0].get('balance_due', 0.0)
        else:
            _logger.warning('Invoice model %s not yet available.', INVOICE_MODEL)

        return revenue, total_outstanding, overdue_count, overdue_amount, total_invoice_value

    # ─── Methods used by dashboard actions / controllers ─────────────────────

    def get_overdue_invoices(self, limit=50, offset=0):
        """
        Return overdue invoices as a paginated list of dicts.
        Overdue rule: due_date < today AND balance_due > 0.
        """
        if INVOICE_MODEL not in self.env:
            return []
        today = date.today()
        domain = [
            ('due_date', '<', str(today)),
            ('balance_due', '>', 0),
            ('status', 'not in', ['cancelled', 'draft']),
        ]
        invoices = self.env[INVOICE_MODEL].search(
            domain,
            limit=limit,
            offset=offset,
            order='due_date asc',
        )
        return invoices.read([
            'invoice_number', 'partner_id', 'due_date',
            'total', 'amount_paid', 'balance_due',
        ])

    def get_recent_payments(self, limit=20, offset=0):
        """Return recent posted payments for the dashboard payment panel."""
        domain = [
            ('state', '=', 'posted'),
            ('payment_date', '>=', str(self.date_from)),
            ('payment_date', '<=', str(self.date_to)),
        ]
        payments = self.env['brightloop.payment'].search(
            domain,
            limit=limit,
            offset=offset,
            order='payment_date desc',
        )
        return payments.read([
            'name', 'partner_id', 'payment_method_id',
            'amount', 'payment_date', 'reference',
            'total_allocated', 'unallocated_amount',
        ])


class BrightloopFinanceReport(models.AbstractModel):
    """
    Abstract model providing reporting utilities.
    Inherited by the XLSX export wizard.
    """
    _name = 'brightloop.finance.report'
    _description = 'Brightloop Finance Report Utilities'

    def _get_payment_summary(self, date_from, date_to, partner_id=None):
        """
        Return a list of payment records for export.
        Applies customer data isolation: non-admin users can only
        see payments for their own partner.
        """
        self._check_report_access(partner_id)

        domain = [
            ('state', '=', 'posted'),
            ('payment_date', '>=', str(date_from)),
            ('payment_date', '<=', str(date_to)),
        ]
        if partner_id:
            domain.append(('partner_id', '=', partner_id))

        return self.env['brightloop.payment'].search(domain, order='payment_date desc')

    def _get_invoice_summary(self, date_from, date_to, status_filter=None,
                              overdue_only=False, partner_id=None):
        """
        Return invoice records for export.
        Enforces customer data isolation.
        """
        self._check_report_access(partner_id)

        if INVOICE_MODEL not in self.env:
            return self.env['brightloop.payment'].browse()  # empty

        domain = [
            ('invoice_date', '>=', str(date_from)),
            ('invoice_date', '<=', str(date_to)),
        ]
        if status_filter:
            domain.append(('status', '=', status_filter))
        if overdue_only:
            domain += [
                ('due_date', '<', str(date.today())),
                ('balance_due', '>', 0),
            ]
        if partner_id:
            domain.append(('partner_id', '=', partner_id))

        return self.env[INVOICE_MODEL].search(domain, order='invoice_date desc')

    def _check_report_access(self, partner_id=None):
        """
        Enforce report authorization:
        - Finance managers: full access
        - Finance users: full access (internal staff)
        - Portal users: only their own partner data

        Raises AccessError if the current user cannot access the requested data.
        """
        user = self.env.user

        # Superuser and finance manager: unrestricted
        if user._is_superuser() or user.has_group(
            'brightloop_finance.group_brightloop_finance_manager'
        ):
            return

        # Finance user (internal staff): full access
        if user.has_group('brightloop_finance.group_brightloop_finance_user'):
            return

        # Portal / customer: can only access their own data
        if partner_id and partner_id != user.partner_id.id:
            raise AccessError(
                _('You do not have access to financial data for this customer.')
            )

        # If no partner filter is set for a portal user, restrict to self
        if not partner_id:
            raise AccessError(
                _('Please specify a customer to access financial reports.')
            )

