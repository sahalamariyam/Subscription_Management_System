# -*- coding: utf-8 -*-
"""
finance_export.py
Member 4 — Brightloop Finance

XLSX export for:
- Payment history
- Invoice details (all, outstanding, overdue)
- Revenue summary
- Subscription information

Uses xlsxwriter for formatting.
Authorization enforced via BrightloopFinanceReport._check_report_access().

Performance: queries use read_group / paginated search.
             Never loads all records into memory without a date filter.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import base64
import io
import logging

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False
    _logger.warning('xlsxwriter not installed. XLSX export will be unavailable.')

# ── Shared constants from brightloop_core (Member 1) ─────────────────────────
# Import canonical subscription status constants to stay in sync with
# shared_constants.py rather than duplicating string literals.
try:
    from odoo.addons.brightloop_core.models.shared_constants import (
        SUBSCRIPTION_STATUS_ACTIVE as _CORE_SUB_ACTIVE,
        SUBSCRIPTION_STATUS_DRAFT as _CORE_SUB_DRAFT,
        SUBSCRIPTION_STATUS_QUOTATION as _CORE_SUB_QUOTATION,
        SUBSCRIPTION_STATUS_CONFIRMED as _CORE_SUB_CONFIRMED,
        SUBSCRIPTION_STATUS_CLOSED as _CORE_SUB_CLOSED,
    )
    _CORE_CONSTANTS_AVAILABLE = True
except ImportError:
    # brightloop_core not yet installed — use inline fallbacks matching shared_constants.py
    _CORE_CONSTANTS_AVAILABLE = False
    _CORE_SUB_ACTIVE    = 'active'
    _CORE_SUB_DRAFT     = 'draft'
    _CORE_SUB_QUOTATION = 'quotation'
    _CORE_SUB_CONFIRMED = 'confirmed'
    _CORE_SUB_CLOSED    = 'closed'

INVOICE_MODEL = 'account.move'          # Confirmed with Member 3 — 2026-10-31
# Confirmed with Member 2 — 2026-10-31
SUBSCRIPTION_MODEL = 'brightloop.subscription'

# account.move payment_state values (Odoo 18)
AM_PAYMENT_PAID     = 'paid'
AM_PAYMENT_REVERSED = 'reversed'
AM_BASE_DOMAIN      = [('move_type', '=', 'out_invoice')]

# Canonical subscription status values sourced from brightloop_core.shared_constants
# (with fallback literals that match those constants exactly)
SUB_STATUS_ACTIVE    = _CORE_SUB_ACTIVE     # 'active'
SUB_STATUS_DRAFT     = _CORE_SUB_DRAFT      # 'draft'
SUB_STATUS_QUOTATION = _CORE_SUB_QUOTATION  # 'quotation'
SUB_STATUS_CONFIRMED = _CORE_SUB_CONFIRMED  # 'confirmed'
SUB_STATUS_CLOSED    = _CORE_SUB_CLOSED     # 'closed'

# Human-readable labels for export sheets — mirrors shared_constants.SUBSCRIPTION_STATUS_SELECTION
STATUS_LABELS = {
    SUB_STATUS_DRAFT:     'Draft',
    SUB_STATUS_QUOTATION: 'Quotation',
    SUB_STATUS_CONFIRMED: 'Confirmed',
    SUB_STATUS_ACTIVE:    'Active',
    SUB_STATUS_CLOSED:    'Closed',
}

# account.move field map (Member 3 confirmed 2026-10-31)
#   brightloop logical   →  account.move field
#   invoice_number       →  name
#   total                →  amount_total
#   balance_due          →  amount_residual
#   amount_paid          →  amount_total - amount_residual  (derived)
#   due_date             →  invoice_date_due
#   status               →  derived from state + payment_state


class BrightloopFinanceExport(models.TransientModel):
    """
    Wizard and export engine for financial XLSX reports.
    Inherits BrightloopFinanceReport for authorization utilities.
    """
    _name = 'brightloop.finance.export'
    _description = 'Brightloop Finance XLSX Export'
    _inherit = 'brightloop.finance.report'

    # ─── Filter fields ────────────────────────────────────────────────────────
    date_from = fields.Date(
        string='From',
        required=True,
        default=lambda self: date.today().replace(month=1, day=1),
    )
    date_to = fields.Date(
        string='To',
        required=True,
        default=fields.Date.context_today,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer (optional)',
        help='Leave blank to export all customers (staff only).',
    )
    subscription_id = fields.Many2one(
        comodel_name='brightloop.subscription',
        string='Subscription (optional)',
        help='Filter invoice/payment export to a specific subscription.',
    )
    export_type = fields.Selection(
        selection=[
            ('payments', 'Payment History'),
            ('invoices_all', 'All Invoices'),
            ('invoices_outstanding', 'Outstanding Invoices'),
            ('invoices_overdue', 'Overdue Invoices'),
            ('revenue_summary', 'Revenue Summary'),
            ('subscriptions', 'Subscription Information'),
            ('full_report', 'Full Financial Report (all sheets)'),
        ],
        string='Report Type',
        required=True,
        default='full_report',
    )

    # ─── Output ───────────────────────────────────────────────────────────────
    file_data = fields.Binary(string='Download', readonly=True, attachment=False)
    file_name = fields.Char(string='File Name', readonly=True)
    state = fields.Selection(
        [('draft', 'Configure'), ('done', 'Download')],
        default='draft',
    )

    # ─── Validation ──────────────────────────────────────────────────────────
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_('Date From must be before Date To.'))

    # ─── Main action ─────────────────────────────────────────────────────────
    def action_generate(self):
        """Generate the XLSX file and set file_data for download."""
        self.ensure_one()

        if not XLSXWRITER_AVAILABLE:
            raise UserError(
                _('xlsxwriter is required for XLSX export. '
                  'Install it with: pip install xlsxwriter')
            )

        # Authorization check
        partner_id      = self.partner_id.id if self.partner_id else None
        subscription_id = self.subscription_id.id if self.subscription_id else None
        self._check_report_access(partner_id)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Shared formats
        fmt = self._build_formats(workbook)

        # Generate requested sheets
        export_type = self.export_type
        if export_type in ('payments', 'full_report'):
            self._write_payments_sheet(workbook, fmt, partner_id)
        if export_type in ('invoices_all', 'full_report'):
            self._write_invoices_sheet(workbook, fmt, partner_id,
                                       subscription_id=subscription_id,
                                       overdue_only=False, label='All Invoices')
        if export_type in ('invoices_outstanding', 'full_report'):
            self._write_invoices_sheet(workbook, fmt, partner_id,
                                       subscription_id=subscription_id,
                                       outstanding_only=True, label='Outstanding')
        if export_type in ('invoices_overdue', 'full_report'):
            self._write_invoices_sheet(workbook, fmt, partner_id,
                                       subscription_id=subscription_id,
                                       overdue_only=True, label='Overdue')
        if export_type in ('revenue_summary', 'full_report'):
            self._write_revenue_summary_sheet(workbook, fmt, partner_id)
        if export_type in ('subscriptions', 'full_report'):
            self._write_subscriptions_sheet(workbook, fmt, partner_id)

        workbook.close()
        output.seek(0)

        file_name = 'brightloop_finance_%s_%s.xlsx' % (
            export_type,
            date.today().strftime('%Y%m%d'),
        )
        self.write({
            'file_data': base64.b64encode(output.read()),
            'file_name': file_name,
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ─── Format helpers ───────────────────────────────────────────────────────
    def _build_formats(self, workbook):
        """Build and return a dict of reusable xlsxwriter formats."""
        return {
            'title': workbook.add_format({
                'bold': True, 'font_size': 14, 'bg_color': '#1F4E79',
                'font_color': 'white', 'border': 1,
            }),
            'header': workbook.add_format({
                'bold': True, 'bg_color': '#2E75B6', 'font_color': 'white',
                'border': 1, 'text_wrap': True, 'valign': 'vcenter',
            }),
            'date': workbook.add_format({
                'num_format': 'DD-MMM-YYYY', 'border': 1,
            }),
            'money': workbook.add_format({
                'num_format': '#,##0.00', 'border': 1,
            }),
            'money_total': workbook.add_format({
                'num_format': '#,##0.00', 'bold': True,
                'bg_color': '#D9E1F2', 'border': 1,
            }),
            'text': workbook.add_format({'border': 1}),
            'text_bold': workbook.add_format({'bold': True, 'border': 1}),
            'overdue': workbook.add_format({
                'border': 1, 'bg_color': '#FFE0E0', 'num_format': '#,##0.00',
            }),
            'label_total': workbook.add_format({
                'bold': True, 'bg_color': '#D9E1F2', 'border': 1,
            }),
        }

    def _write_sheet_title(self, ws, fmt, title, date_from, date_to, col_count):
        """Write a two-row header banner to the worksheet."""
        ws.merge_range(0, 0, 0, col_count - 1, title, fmt['title'])
        ws.merge_range(
            1, 0, 1, col_count - 1,
            'Period: %s to %s  |  Generated: %s' % (
                date_from.strftime('%d %b %Y'),
                date_to.strftime('%d %b %Y'),
                date.today().strftime('%d %b %Y'),
            ),
            fmt['text'],
        )
        return 3  # next data row

    # ─── Payments sheet ───────────────────────────────────────────────────────
    def _write_payments_sheet(self, workbook, fmt, partner_id):
        ws = workbook.add_worksheet('Payment History')
        ws.set_column('A:A', 18)
        ws.set_column('B:B', 22)
        ws.set_column('C:D', 14)
        ws.set_column('E:F', 15)
        ws.set_column('G:G', 22)
        ws.set_column('H:H', 12)

        headers = ['Payment Ref', 'Customer', 'Method', 'Date',
                   'Amount', 'Allocated', 'Unallocated', 'Status']
        row = self._write_sheet_title(ws, fmt, 'Payment History', self.date_from, self.date_to, len(headers))
        for col, h in enumerate(headers):
            ws.write(row, col, h, fmt['header'])
        row += 1

        payments = self._get_payment_summary(self.date_from, self.date_to, partner_id)
        total_amount = total_allocated = total_unallocated = 0.0

        for p in payments:
            ws.write(row, 0, p.name, fmt['text'])
            ws.write(row, 1, p.partner_id.display_name, fmt['text'])
            ws.write(row, 2, p.payment_method_id.name, fmt['text'])
            ws.write_datetime(row, 3, p.payment_date, fmt['date'])
            ws.write(row, 4, p.amount, fmt['money'])
            ws.write(row, 5, p.total_allocated, fmt['money'])
            ws.write(row, 6, p.unallocated_amount, fmt['money'])
            ws.write(row, 7, dict(p._fields['state'].selection).get(p.state, p.state), fmt['text'])
            total_amount += p.amount
            total_allocated += p.total_allocated
            total_unallocated += p.unallocated_amount
            row += 1

        # Totals row
        ws.write(row, 3, 'TOTAL', fmt['label_total'])
        ws.write(row, 4, total_amount, fmt['money_total'])
        ws.write(row, 5, total_allocated, fmt['money_total'])
        ws.write(row, 6, total_unallocated, fmt['money_total'])

    # ─── Invoices sheet ───────────────────────────────────────────────────────
    def _write_invoices_sheet(self, workbook, fmt, partner_id,
                               overdue_only=False, outstanding_only=False,
                               subscription_id=None, label='Invoices'):
        ws = workbook.add_worksheet(label[:31])
        ws.set_column('A:B', 18)
        ws.set_column('C:C', 22)
        ws.set_column('D:F', 14)
        ws.set_column('G:I', 15)

        headers = ['Invoice #', 'Subscription', 'Customer', 'Payment State',
                   'Invoice Date', 'Due Date', 'Total', 'Amount Paid', 'Balance Due']
        row = self._write_sheet_title(ws, fmt, label, self.date_from, self.date_to, len(headers))
        for col, h in enumerate(headers):
            ws.write(row, col, h, fmt['header'])
        row += 1

        today = date.today()
        invoices = self._get_invoice_summary(
            self.date_from, self.date_to,
            overdue_only=overdue_only,
            partner_id=partner_id,
            subscription_id=subscription_id,
        )
        if outstanding_only and not overdue_only:
            invoices = invoices.filtered(lambda i: i.amount_residual > 0)

        # Human-readable payment_state labels (Odoo 18 account.move)
        PAYMENT_STATE_LABELS = {
            'not_paid':       'Not Paid',
            'partial':        'Partially Paid',
            'in_payment':     'In Payment',
            'paid':           'Paid',
            'reversed':       'Reversed',
            'invoicing_legacy': 'Legacy',
        }

        total_total = total_paid = total_balance = 0.0

        for inv in invoices:
            # account.move field mapping (Member 3 confirmed 2026-10-31)
            inv_number  = inv.name or ''
            inv_sub     = inv.subscription_id.display_name if inv.subscription_id else ''
            inv_partner = inv.partner_id.display_name if inv.partner_id else ''
            pay_state   = PAYMENT_STATE_LABELS.get(inv.payment_state, inv.payment_state or '')
            inv_date    = inv.invoice_date
            due_date    = inv.invoice_date_due
            total       = inv.amount_total or 0.0
            balance     = inv.amount_residual or 0.0
            paid        = total - balance           # derived: amount_total - amount_residual

            is_overdue  = due_date and due_date < today and balance > 0
            money_fmt   = fmt['overdue'] if is_overdue else fmt['money']

            ws.write(row, 0, inv_number, fmt['text'])
            ws.write(row, 1, inv_sub, fmt['text'])
            ws.write(row, 2, inv_partner, fmt['text'])
            ws.write(row, 3, pay_state, fmt['text'])
            ws.write_datetime(row, 4, inv_date, fmt['date']) if inv_date else ws.write(row, 4, '', fmt['text'])
            ws.write_datetime(row, 5, due_date, fmt['date']) if due_date else ws.write(row, 5, '', fmt['text'])
            ws.write(row, 6, total, money_fmt)
            ws.write(row, 7, paid, money_fmt)
            ws.write(row, 8, balance, money_fmt)
            total_total   += total
            total_paid    += paid
            total_balance += balance
            row += 1

        ws.write(row, 5, 'TOTAL', fmt['label_total'])
        ws.write(row, 6, total_total, fmt['money_total'])
        ws.write(row, 7, total_paid, fmt['money_total'])
        ws.write(row, 8, total_balance, fmt['money_total'])

    # ─── Revenue summary sheet ────────────────────────────────────────────────
    def _write_revenue_summary_sheet(self, workbook, fmt, partner_id):
        """
        Revenue Summary sheet — 4 columns per calendar month:
          A  Month label        (e.g. 'October 2026')
          B  Revenue Received   (sum of allocated_amount from posted payments)
          C  Total Invoiced     (sum of amount_total from posted account.move invoices)
          D  Outstanding        (sum of amount_residual from those same invoices)

        Sources:
          B → brightloop.invoice.payment grouped by allocation_date:month
          C, D → account.move (Odoo 18, confirmed Member 3) grouped by invoice_date:month
        """
        ws = workbook.add_worksheet('Revenue Summary')
        ws.set_column('A:A', 20)
        ws.set_column('B:D', 16)

        headers = ['Month', 'Revenue Received', 'Total Invoiced', 'Outstanding Balance']
        row = self._write_sheet_title(ws, fmt, 'Revenue Summary', self.date_from, self.date_to, len(headers))
        for col, h in enumerate(headers):
            ws.write(row, col, h, fmt['header'])
        row += 1

        date_from_str = str(self.date_from)
        date_to_str   = str(self.date_to)

        # ── Column B: Revenue received per month (from our allocation records) ──
        payment_domain = [
            ('payment_id.state', '=', 'posted'),
            ('allocation_date', '>=', date_from_str),
            ('allocation_date', '<=', date_to_str),
        ]
        if partner_id:
            payment_domain.append(('partner_id', '=', partner_id))

        revenue_data = self.env['brightloop.invoice.payment'].read_group(
            domain=payment_domain,
            fields=['allocated_amount:sum'],
            groupby=['allocation_date:month'],
            orderby='allocation_date asc',
        )
        # Build lookup: month_label → revenue_received
        revenue_by_month = {}
        for r in revenue_data:
            key = r.get('allocation_date:month', '')
            revenue_by_month[key] = r.get('allocated_amount', 0.0) or 0.0

        # ── Columns C & D: Invoiced and Outstanding per month (account.move) ──
        # Uses Odoo 18 native invoice model confirmed by Member 3
        invoiced_by_month    = {}
        outstanding_by_month = {}

        if INVOICE_MODEL in self.env:
            inv_base_domain = AM_BASE_DOMAIN + [
                ('state', '=', 'posted'),
                ('invoice_date', '>=', date_from_str),
                ('invoice_date', '<=', date_to_str),
            ]
            if partner_id:
                inv_base_domain.append(('partner_id', '=', partner_id))

            # Total invoiced per month (amount_total)
            inv_data = self.env[INVOICE_MODEL].read_group(
                domain=inv_base_domain,
                fields=['amount_total:sum'],
                groupby=['invoice_date:month'],
                orderby='invoice_date asc',
            )
            for r in inv_data:
                key = r.get('invoice_date:month', '')
                invoiced_by_month[key] = r.get('amount_total', 0.0) or 0.0

            # Outstanding per month (amount_residual, only where > 0)
            out_data = self.env[INVOICE_MODEL].read_group(
                domain=inv_base_domain + [('amount_residual', '>', 0)],
                fields=['amount_residual:sum'],
                groupby=['invoice_date:month'],
                orderby='invoice_date asc',
            )
            for r in out_data:
                key = r.get('invoice_date:month', '')
                outstanding_by_month[key] = r.get('amount_residual', 0.0) or 0.0
        else:
            _logger.warning(
                'brightloop_finance: %s not available — Revenue Summary C/D columns will be empty.',
                INVOICE_MODEL,
            )

        # ── Merge all months from all three sources ───────────────────────────
        all_months = sorted(
            set(revenue_by_month) | set(invoiced_by_month) | set(outstanding_by_month)
        )

        total_revenue     = 0.0
        total_invoiced    = 0.0
        total_outstanding = 0.0

        for month_key in all_months:
            revenue     = revenue_by_month.get(month_key, 0.0)
            invoiced    = invoiced_by_month.get(month_key, 0.0)
            outstanding = outstanding_by_month.get(month_key, 0.0)

            ws.write(row, 0, month_key,    fmt['text'])
            ws.write(row, 1, revenue,      fmt['money'])
            ws.write(row, 2, invoiced,     fmt['money'])
            ws.write(row, 3, outstanding,  fmt['money'])

            total_revenue     += revenue
            total_invoiced    += invoiced
            total_outstanding += outstanding
            row += 1

        # Totals row
        ws.write(row, 0, 'TOTAL',          fmt['label_total'])
        ws.write(row, 1, total_revenue,    fmt['money_total'])
        ws.write(row, 2, total_invoiced,   fmt['money_total'])
        ws.write(row, 3, total_outstanding, fmt['money_total'])

    # ─── Subscriptions sheet ─────────────────────────────────────────────────
    def _write_subscriptions_sheet(self, workbook, fmt, partner_id):
        ws = workbook.add_worksheet('Subscriptions')
        ws.set_column('A:B', 20)
        ws.set_column('C:C', 22)
        ws.set_column('D:E', 12)
        ws.set_column('F:H', 14)

        # Confirmed fields (Member 2, 2026-10-31):
        # subscription_number, plan_id, partner_id/customer_id (alias),
        # status, is_paused, start_date, expiry_date, next_billing_date
        headers = [
            'Subscription #', 'Plan', 'Customer',
            'Status', 'Paused',
            'Start Date', 'Expiry Date', 'Next Billing',
        ]
        row = self._write_sheet_title(
            ws, fmt, 'Subscriptions', self.date_from, self.date_to, len(headers)
        )
        for col, h in enumerate(headers):
            ws.write(row, col, h, fmt['header'])
        row += 1

        if SUBSCRIPTION_MODEL not in self.env:
            ws.write(row, 0, 'Subscription model not yet available.', fmt['text'])
            return

        # Filter by partner_id (primary Odoo field);
        # customer_id is a confirmed alias — both work.
        domain = [('status', 'not in', ['draft'])]
        if partner_id:
            domain.append(('partner_id', '=', partner_id))

        subs = self.env[SUBSCRIPTION_MODEL].search(domain, order='start_date desc')

        # STATUS_LABELS is the module-level dict sourced from brightloop_core.shared_constants
        for s in subs:
            # Use partner_id (Odoo standard); fall back to customer_id alias
            customer = (
                s.partner_id.display_name
                if hasattr(s, 'partner_id') and s.partner_id
                else (s.customer_id.display_name if hasattr(s, 'customer_id') and s.customer_id else '')
            )
            status_label = STATUS_LABELS.get(s.status, s.status or '')
            # is_paused confirmed field (Member 2); guard with hasattr for safety
            is_paused = getattr(s, 'is_paused', False)

            ws.write(row, 0, s.subscription_number or '', fmt['text'])
            ws.write(row, 1, s.plan_id.display_name if s.plan_id else '', fmt['text'])
            ws.write(row, 2, customer, fmt['text'])
            ws.write(row, 3, status_label, fmt['text'])
            ws.write(row, 4, 'Yes' if is_paused else 'No', fmt['text'])

            if s.start_date:
                ws.write_datetime(row, 5, s.start_date, fmt['date'])
            else:
                ws.write(row, 5, '', fmt['text'])

            if s.expiry_date:
                ws.write_datetime(row, 6, s.expiry_date, fmt['date'])
            else:
                ws.write(row, 6, '', fmt['text'])

            if s.next_billing_date:
                ws.write_datetime(row, 7, s.next_billing_date, fmt['date'])
            else:
                ws.write(row, 7, '', fmt['text'])

            row += 1

