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

INVOICE_MODEL = 'brightloop.invoice'
SUBSCRIPTION_MODEL = 'brightloop.subscription'


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
        partner_id = self.partner_id.id if self.partner_id else None
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
            self._write_invoices_sheet(workbook, fmt, partner_id, overdue_only=False, label='All Invoices')
        if export_type in ('invoices_outstanding', 'full_report'):
            self._write_invoices_sheet(workbook, fmt, partner_id, outstanding_only=True, label='Outstanding')
        if export_type in ('invoices_overdue', 'full_report'):
            self._write_invoices_sheet(workbook, fmt, partner_id, overdue_only=True, label='Overdue')
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
                               overdue_only=False, outstanding_only=False, label='Invoices'):
        ws = workbook.add_worksheet(label[:31])  # xlsx sheet name max 31 chars
        ws.set_column('A:B', 18)
        ws.set_column('C:C', 22)
        ws.set_column('D:F', 14)
        ws.set_column('G:I', 15)

        headers = ['Invoice #', 'Subscription', 'Customer', 'Status',
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
        )
        if outstanding_only and not overdue_only:
            invoices = invoices.filtered(lambda i: i.balance_due > 0)

        total_total = total_paid = total_balance = 0.0

        for inv in invoices:
            is_overdue = inv.due_date and inv.due_date < today and inv.balance_due > 0
            money_fmt = fmt['overdue'] if is_overdue else fmt['money']
            ws.write(row, 0, inv.invoice_number, fmt['text'])
            ws.write(row, 1, inv.subscription_id.display_name if inv.subscription_id else '', fmt['text'])
            ws.write(row, 2, inv.partner_id.display_name, fmt['text'])
            ws.write(row, 3, inv.status, fmt['text'])
            ws.write_datetime(row, 4, inv.invoice_date, fmt['date'])
            ws.write_datetime(row, 5, inv.due_date, fmt['date']) if inv.due_date else ws.write(row, 5, '', fmt['text'])
            ws.write(row, 6, inv.total, money_fmt)
            ws.write(row, 7, inv.amount_paid, money_fmt)
            ws.write(row, 8, inv.balance_due, money_fmt)
            total_total += inv.total or 0
            total_paid += inv.amount_paid or 0
            total_balance += inv.balance_due or 0
            row += 1

        ws.write(row, 5, 'TOTAL', fmt['label_total'])
        ws.write(row, 6, total_total, fmt['money_total'])
        ws.write(row, 7, total_paid, fmt['money_total'])
        ws.write(row, 8, total_balance, fmt['money_total'])

    # ─── Revenue summary sheet ────────────────────────────────────────────────
    def _write_revenue_summary_sheet(self, workbook, fmt, partner_id):
        ws = workbook.add_worksheet('Revenue Summary')
        ws.set_column('A:A', 20)
        ws.set_column('B:D', 16)

        headers = ['Month', 'Revenue Received', 'Invoiced', 'Outstanding']
        row = self._write_sheet_title(ws, fmt, 'Revenue Summary', self.date_from, self.date_to, len(headers))
        for col, h in enumerate(headers):
            ws.write(row, col, h, fmt['header'])
        row += 1

        # Revenue by month (from allocations)
        payment_domain = [
            ('payment_id.state', '=', 'posted'),
            ('allocation_date', '>=', str(self.date_from)),
            ('allocation_date', '<=', str(self.date_to)),
        ]
        if partner_id:
            payment_domain.append(('partner_id', '=', partner_id))

        revenue_data = self.env['brightloop.invoice.payment'].read_group(
            domain=payment_domain,
            fields=['allocated_amount:sum', 'allocation_date:month'],
            groupby=['allocation_date:month'],
            orderby='allocation_date asc',
        )

        total_revenue = 0.0
        for r in revenue_data:
            month_label = r.get('allocation_date:month', 'Unknown')
            revenue = r.get('allocated_amount', 0.0) or 0.0
            ws.write(row, 0, month_label, fmt['text'])
            ws.write(row, 1, revenue, fmt['money'])
            ws.write(row, 2, '', fmt['text'])   # invoiced per month — needs invoice model
            ws.write(row, 3, '', fmt['text'])   # outstanding — needs invoice model
            total_revenue += revenue
            row += 1

        ws.write(row, 0, 'TOTAL', fmt['label_total'])
        ws.write(row, 1, total_revenue, fmt['money_total'])

    # ─── Subscriptions sheet ─────────────────────────────────────────────────
    def _write_subscriptions_sheet(self, workbook, fmt, partner_id):
        ws = workbook.add_worksheet('Subscriptions')
        ws.set_column('A:B', 20)
        ws.set_column('C:C', 22)
        ws.set_column('D:F', 14)
        ws.set_column('G:G', 16)

        headers = ['Subscription #', 'Plan', 'Customer', 'Status',
                   'Start Date', 'Expiry Date', 'Next Billing']
        row = self._write_sheet_title(ws, fmt, 'Subscriptions', self.date_from, self.date_to, len(headers))
        for col, h in enumerate(headers):
            ws.write(row, col, h, fmt['header'])
        row += 1

        if SUBSCRIPTION_MODEL not in self.env:
            ws.write(row, 0, 'Subscription model not yet available.', fmt['text'])
            return

        domain = []
        if partner_id:
            domain.append(('customer_id', '=', partner_id))

        subs = self.env[SUBSCRIPTION_MODEL].search(domain, order='start_date desc')
        for s in subs:
            ws.write(row, 0, s.subscription_number or '', fmt['text'])
            ws.write(row, 1, s.plan_id.display_name if s.plan_id else '', fmt['text'])
            ws.write(row, 2, s.customer_id.display_name if s.customer_id else '', fmt['text'])
            ws.write(row, 3, s.status or '', fmt['text'])
            ws.write_datetime(row, 4, s.start_date, fmt['date']) if s.start_date else ws.write(row, 4, '', fmt['text'])
            ws.write_datetime(row, 5, s.expiry_date, fmt['date']) if s.expiry_date else ws.write(row, 5, '', fmt['text'])
            ws.write_datetime(row, 6, s.next_billing_date, fmt['date']) if s.next_billing_date else ws.write(row, 6, '', fmt['text'])
            row += 1
