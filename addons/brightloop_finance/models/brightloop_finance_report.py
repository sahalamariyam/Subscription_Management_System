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

  Member 3 (account.move — Odoo 18 native):
    _name           = 'account.move'              ✅ confirmed 2026-10-31
    move_type       = 'out_invoice'               ✅ customer invoices only
    amount_total    = total invoice amount        ✅ (was: total)
    amount_residual = outstanding balance         ✅ (was: balance_due)
    amount_paid     = amount_total-amount_residual✅ derived, not stored
    partner_id      = res.partner                 ✅ same
    invoice_date_due= due date                    ✅ (was: due_date)
    invoice_date    = invoice date                ✅ same
    name            = invoice number/ref          ✅ (was: invoice_number)
    subscription_id = Many2one(brightloop.sub)    ✅ confirmed 2026-10-31 (Member 3 adds via _inherit on account.move in brightloop_billing)
    state: draft | posted | cancel               ✅ confirmed
    payment_state: not_paid | partial | in_payment | paid | reversed ✅
"""

from odoo import api, fields, models, _
from odoo.exceptions import AccessError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

# ── Shared constants from brightloop_core (Member 1) ─────────────────────────
# Imported at function-call time to avoid import-time circular issues.
# Use helper below: _get_sub_const()
try:
    from odoo.addons.brightloop_core.models.shared_constants import (
        SUBSCRIPTION_STATUS_ACTIVE as _CORE_SUB_ACTIVE,
    )
    _CORE_CONSTANTS_AVAILABLE = True
except ImportError:
    # brightloop_core not yet installed in this environment — use inline fallback
    _CORE_CONSTANTS_AVAILABLE = False
    _CORE_SUB_ACTIVE = 'active'

# ── Integration constants ─────────────────────────────────────────────────────
# Member 3 confirmed 2026-10-31: using native account.move (Odoo 18 Community)
INVOICE_MODEL    = 'account.move'
# Member 2 confirmed 2026-10-31
SUBSCRIPTION_MODEL = 'brightloop.subscription'

# Canonical subscription active status — sourced from brightloop_core.shared_constants
# Fallback value 'active' matches shared_constants.SUBSCRIPTION_STATUS_ACTIVE
SUB_STATUS_ACTIVE = _CORE_SUB_ACTIVE

# account.move field map (Member 3 confirmed 2026-10-31)
# brightloop logical name  →  account.move field
#   total                  →  amount_total
#   balance_due            →  amount_residual
#   amount_paid            →  amount_total - amount_residual  (derived)
#   due_date               →  invoice_date_due
#   invoice_number         →  name
#   status (draft)         →  state = 'draft'
#   status (confirmed)     →  state = 'posted', payment_state != 'paid'
#   status (paid)          →  state = 'posted', payment_state = 'paid'
#   status (cancelled)     →  state = 'cancel'
#   partner_id             →  partner_id  (unchanged)

# account.move payment_state values (Odoo 18)
AM_PAYMENT_PAID     = 'paid'
AM_PAYMENT_PARTIAL  = 'partial'
AM_PAYMENT_IN_PAY   = 'in_payment'
AM_PAYMENT_NOT_PAID = 'not_paid'
AM_PAYMENT_REVERSED = 'reversed'

# Base domain for ALL customer invoices (apply to every account.move query)
AM_BASE_DOMAIN = [('move_type', '=', 'out_invoice')]


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

        Invoice source: account.move (Odoo 18, confirmed Member 3 2026-10-31)
        Field mapping:
          total       → amount_total
          balance_due → amount_residual
          due_date    → invoice_date_due
          status      → derived from state + payment_state
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

        # ── Invoice aggregation via account.move ──────────────────────────
        total_invoice_value = 0.0
        total_outstanding   = 0.0
        overdue_count       = 0
        overdue_amount      = 0.0

        if INVOICE_MODEL in self.env:
            # All posted customer invoices in the date period
            inv_domain = AM_BASE_DOMAIN + [
                ('state', '=', 'posted'),
                ('invoice_date', '>=', str(date_from)),
                ('invoice_date', '<=', str(date_to)),
            ]
            inv_data = self.env[INVOICE_MODEL].read_group(
                domain=inv_domain,
                fields=['amount_total:sum'],
                groupby=[],
            )
            total_invoice_value = inv_data[0]['amount_total'] if inv_data else 0.0

            # Outstanding: posted invoices with residual > 0
            outstanding_domain = inv_domain + [('amount_residual', '>', 0)]
            out_data = self.env[INVOICE_MODEL].read_group(
                domain=outstanding_domain,
                fields=['amount_residual:sum'],
                groupby=[],
            )
            total_outstanding = out_data[0]['amount_residual'] if out_data else 0.0

            # Overdue: posted, not fully paid, past due date
            # Excludes reversed invoices (credit notes etc.)
            overdue_domain = AM_BASE_DOMAIN + [
                ('state', '=', 'posted'),
                ('payment_state', 'not in', [AM_PAYMENT_PAID, AM_PAYMENT_REVERSED]),
                ('amount_residual', '>', 0),
                ('invoice_date_due', '<', str(today)),
            ]
            overdue_data = self.env[INVOICE_MODEL].read_group(
                domain=overdue_domain,
                fields=['amount_residual:sum', 'id:count'],
                groupby=[],
            )
            if overdue_data:
                overdue_count  = overdue_data[0].get('__count', 0)
                overdue_amount = overdue_data[0].get('amount_residual', 0.0)
        else:
            _logger.warning('Invoice model %s not yet available.', INVOICE_MODEL)

        return revenue, total_outstanding, overdue_count, overdue_amount, total_invoice_value

    # ─── Methods used by dashboard actions / controllers ─────────────────────

    def get_overdue_invoices(self, limit=50, offset=0):
        """
        Return overdue invoices as a paginated list of dicts.
        Overdue rule: invoice_date_due < today AND amount_residual > 0.
        Source: account.move (Odoo 18, confirmed Member 3 2026-10-31)
        """
        if INVOICE_MODEL not in self.env:
            return []
        today = date.today()
        domain = AM_BASE_DOMAIN + [
            ('state', '=', 'posted'),
            ('payment_state', 'not in', [AM_PAYMENT_PAID, AM_PAYMENT_REVERSED]),
            ('amount_residual', '>', 0),
            ('invoice_date_due', '<', str(today)),
        ]
        invoices = self.env[INVOICE_MODEL].search(
            domain,
            limit=limit,
            offset=offset,
            order='invoice_date_due asc',
        )
        return invoices.read([
            'name', 'partner_id', 'invoice_date_due',
            'amount_total', 'amount_residual',
            'payment_state', 'subscription_id',   # subscription_id confirmed ✅
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
                              overdue_only=False, partner_id=None,
                              subscription_id=None):
        """
        Return invoice records for export.
        Source: account.move (Odoo 18, confirmed Member 3 2026-10-31)
        subscription_id field confirmed ✅ — added by Member 3 via _inherit.
        Enforces customer data isolation.
        """
        self._check_report_access(partner_id)

        if INVOICE_MODEL not in self.env:
            return self.env['brightloop.payment'].browse()  # empty recordset

        # Base: posted customer invoices in date range
        domain = AM_BASE_DOMAIN + [
            ('state', '=', 'posted'),
            ('invoice_date', '>=', str(date_from)),
            ('invoice_date', '<=', str(date_to)),
        ]
        if overdue_only:
            domain += [
                ('payment_state', 'not in', [AM_PAYMENT_PAID, AM_PAYMENT_REVERSED]),
                ('amount_residual', '>', 0),
                ('invoice_date_due', '<', str(date.today())),
            ]
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        if subscription_id:
            domain.append(('subscription_id', '=', subscription_id))

        return self.env[INVOICE_MODEL].search(domain, order='invoice_date desc')

    def _check_report_access(self, partner_id=None):
        """
        Enforce report authorization:
        - Superuser: unrestricted
        - brightloop_core.group_brightloop_admin (Member 1): unrestricted
        - brightloop_finance.group_brightloop_finance_manager: unrestricted
        - brightloop_finance.group_brightloop_finance_user (internal staff): full access
        - brightloop_core.group_brightloop_customer / portal: only their own data

        Raises AccessError if the current user cannot access the requested data.
        """
        user = self.env.user

        # Superuser: always unrestricted
        if user._is_superuser():
            return

        # Brightloop admin (Member 1 core role) or Finance Manager: unrestricted
        # Note: Finance Manager already implies brightloop_core.group_brightloop_admin,
        # but we check both explicitly for clarity and forward-compatibility.
        if (
            user.has_group('brightloop_core.group_brightloop_admin')
            or user.has_group('brightloop_finance.group_brightloop_finance_manager')
        ):
            return

        # Finance user (internal staff, implies brightloop_core.group_brightloop_staff):
        # full read access to all records
        if user.has_group('brightloop_finance.group_brightloop_finance_user'):
            return

        # Customer / portal user (brightloop_core.group_brightloop_customer):
        # can only access their own partner data
        if partner_id and partner_id != user.partner_id.id:
            raise AccessError(
                _('You do not have access to financial data for this customer.')
            )

        # Portal user with no partner filter — refuse (would leak all data)
        if not partner_id:
            raise AccessError(
                _('Please specify a customer to access financial reports.')
            )

