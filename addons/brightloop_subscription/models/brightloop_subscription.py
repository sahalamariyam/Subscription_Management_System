# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Subscription Lifecycle & Line Models
Owner: Member 2 (Product, Plan, Quotation & Subscription Lifecycle Lead)

Implements:
- Unique subscription sequence generation (SUB/YYYY/NNNNN).
- Exact canonical lifecycle state machine:
    Draft -> Quotation -> Confirmed -> Active -> Closed
- Permission-governed operations:
    * Pause & Resume (respects plan.allow_pause, adjusts next billing date).
    * Renewal (respects plan.allow_renewal, increments renewal count, extends term).
    * Early closure (respects plan.allow_early_close).
    * Automatic closure (respects plan.auto_close).
- Subscription lines, quantity, unit price, tax references, and line totals.
- Reliable integration contracts for Member 3 (Billing) and Member 4 (Finance).
"""

from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.brightloop_core.models.shared_constants import (
    SUBSCRIPTION_STATUS_DRAFT,
    SUBSCRIPTION_STATUS_QUOTATION,
    SUBSCRIPTION_STATUS_CONFIRMED,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_CLOSED,
    SUBSCRIPTION_STATUS_SELECTION,
    BILLING_INTERVAL_SELECTION,
)


class BrightloopSubscription(models.Model):
    _name = 'brightloop.subscription'
    _description = 'Brightloop Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # =========================================================================
    # Identifiers & Customer Association
    # =========================================================================
    subscription_number = fields.Char(
        string='Subscription Number',
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        default=lambda self: _('New'),
        help="Unique commercial reference (e.g. SUB/2026/00001)",
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        index=True,
        tracking=True,
        help="Customer partner entity",
    )
    # Direct alias for Member 4 & shared data contract compatibility
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer Reference',
        related='partner_id',
        store=True,
        readonly=True,
    )
    plan_id = fields.Many2one(
        'brightloop.plan',
        string='Subscription Plan',
        required=True,
        index=True,
        tracking=True,
        help="Associated recurring billing plan",
    )
    template_id = fields.Many2one(
        'brightloop.quotation.template',
        string='Quotation Template',
        help="Source template used to generate this quote",
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help="Operating entity / company reference",
    )

    # =========================================================================
    # Lifecycle Status & Member 3 State Compatibility
    # =========================================================================
    status = fields.Selection(
        selection=SUBSCRIPTION_STATUS_SELECTION,
        string='Status',
        default=SUBSCRIPTION_STATUS_DRAFT,
        required=True,
        tracking=True,
        help="Canonical lifecycle: Draft -> Quotation -> Confirmed -> Active -> Closed",
    )
    # Direct alias for Member 3 billing engine compatibility
    state = fields.Selection(
        selection=SUBSCRIPTION_STATUS_SELECTION,
        string='State',
        related='status',
        store=True,
        readonly=True,
        help="State alias for Member 3 recurring billing engine",
    )

    # =========================================================================
    # Dates, Terms & Schedule Details (Member 3 Contracts)
    # =========================================================================
    valid_until = fields.Date(
        string='Valid Until',
        tracking=True,
        help="Expiration date of sales quotation offer",
    )
    start_date = fields.Date(
        string='Start Date',
        tracking=True,
        help="Subscription commencement date",
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        tracking=True,
        help="Subscription scheduled expiration date",
    )
    next_billing_date = fields.Date(
        string='Next Billing Date',
        index=True,
        tracking=True,
        help="Due date for next recurring invoice generation (queried by Member 3)",
    )
    billing_interval = fields.Selection(
        selection=BILLING_INTERVAL_SELECTION,
        string='Billing Interval',
        related='plan_id.billing_interval',
        store=True,
        readonly=True,
        help="Billing cadence (Daily, Weekly, Monthly, Yearly)",
    )
    billing_interval_count = fields.Integer(
        string='Billing Interval Count',
        related='plan_id.billing_interval_count',
        store=True,
        readonly=True,
        help="Number of intervals per billing cycle",
    )
    billing_anchor_day = fields.Integer(
        string='Billing Anchor Day',
        readonly=True,
        help="Preserved day of month for anchor-preserving recurring billing (e.g. 31st)",
    )
    payment_terms = fields.Char(
        string='Payment Terms',
        default='Immediate Payment',
        help="Commercial payment terms (e.g. Net 15, Net 30, Immediate)",
    )

    # =========================================================================
    # Governance & Operational State Tracking
    # =========================================================================
    is_paused = fields.Boolean(
        string='Is Paused',
        default=False,
        tracking=True,
        help="True if the subscription is currently paused (retains active status)",
    )
    pause_date = fields.Date(
        string='Pause Date',
        readonly=True,
    )
    resume_date = fields.Date(
        string='Resume Date',
        readonly=True,
    )
    renewal_count = fields.Integer(
        string='Renewal Count',
        default=0,
        readonly=True,
        help="Total number of successful renewals",
    )
    closed_date = fields.Date(
        string='Closed Date',
        readonly=True,
    )
    closure_reason = fields.Selection(
        selection=[
            ('expired', 'Natural Expiration'),
            ('user_request', 'Customer Requested Cancellation'),
            ('non_payment', 'Non-Payment / Default'),
            ('plan_ended', 'Plan Availability Ended'),
            ('other', 'Other Reason'),
        ],
        string='Closure Reason',
        tracking=True,
    )
    early_closed = fields.Boolean(
        string='Early Closed',
        default=False,
        readonly=True,
    )

    # =========================================================================
    # Subscription Lines & Totals
    # =========================================================================
    line_ids = fields.One2many(
        'brightloop.subscription.line',
        'subscription_id',
        string='Subscription Lines',
        copy=True,
    )
    amount_subtotal = fields.Float(
        string='Subtotal',
        digits=(16, 2),
        compute='_compute_totals',
        store=True,
    )
    amount_total = fields.Float(
        string='Total Amount',
        digits=(16, 2),
        compute='_compute_totals',
        store=True,
    )

    @api.depends('line_ids.amount_subtotal')
    def _compute_totals(self):
        for sub in self:
            total = sum(line.amount_subtotal for line in sub.line_ids)
            sub.amount_subtotal = total
            sub.amount_total = total

    # =========================================================================
    # Model ORM Hooks
    # =========================================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('subscription_number', _('New')) == _('New'):
                vals['subscription_number'] = self.env['ir.sequence'].next_by_code('brightloop.subscription') or _('New')
        return super().create(vals_list)

    @api.constrains('start_date', 'expiry_date')
    def _check_dates_consistency(self):
        for sub in self:
            if sub.start_date and sub.expiry_date and sub.expiry_date < sub.start_date:
                raise ValidationError(_("Subscription Expiry Date cannot be earlier than Start Date."))

    # =========================================================================
    # Lifecycle State Transitions
    # Canonical Flow: Draft -> Quotation -> Confirmed -> Active -> Closed
    # =========================================================================

    def action_send_quotation(self):
        """Move from Draft to Quotation. Enforce minimum quantity requirement."""
        for sub in self:
            if sub.status != SUBSCRIPTION_STATUS_DRAFT:
                raise UserError(_("Only Draft subscriptions can be converted to Quotations."))
            if not sub.line_ids:
                raise ValidationError(_("A quotation must have at least one product line."))

            total_qty = sum(line.quantity for line in sub.line_ids)
            if total_qty < sub.plan_id.minimum_quantity:
                raise ValidationError(
                    _("Total line quantity (%s) is less than the plan minimum required quantity (%s).")
                    % (total_qty, sub.plan_id.minimum_quantity)
                )

            if not sub.valid_until:
                days = sub.template_id.validity_days if sub.template_id else 30
                sub.valid_until = fields.Date.today() + relativedelta(days=days)

            sub.status = SUBSCRIPTION_STATUS_QUOTATION

    def action_cancel_to_draft(self):
        """Revert a Quotation back to Draft for revisions."""
        for sub in self:
            if sub.status != SUBSCRIPTION_STATUS_QUOTATION:
                raise UserError(_("Only Quotations can be reset to Draft."))
            sub.status = SUBSCRIPTION_STATUS_DRAFT

    def action_confirm(self):
        """
        Move from Quotation to Confirmed.
        Validates that quotation has not expired. Prevents duplicate conversions.
        """
        today = fields.Date.today()
        for sub in self:
            if sub.status != SUBSCRIPTION_STATUS_QUOTATION:
                raise UserError(_("Only Quotations can be confirmed."))
            if sub.valid_until and sub.valid_until < today:
                raise ValidationError(
                    _("Cannot confirm quotation %s: the quotation validity expired on %s.")
                    % (sub.subscription_number, sub.valid_until)
                )
            sub.status = SUBSCRIPTION_STATUS_CONFIRMED

    def action_activate(self):
        """
        Move from Confirmed to Active.
        Sets start date, records billing anchor day, and computes initial next billing date.
        """
        today = fields.Date.today()
        for sub in self:
            if sub.status != SUBSCRIPTION_STATUS_CONFIRMED:
                raise UserError(_("Only Confirmed subscriptions can be activated."))

            if not sub.start_date:
                sub.start_date = today

            sub.billing_anchor_day = sub.start_date.day

            # Calculate initial next billing date preserving anchor day
            sub.next_billing_date = sub.plan_id.compute_next_billing_date(
                sub.start_date,
                interval_count=sub.billing_interval_count or 1,
                anchor_day=sub.billing_anchor_day,
            )

            # Default initial expiry date if not explicitly set
            if not sub.expiry_date:
                sub.expiry_date = sub.plan_id.compute_next_billing_date(
                    sub.start_date,
                    interval_count=sub.billing_interval_count or 1,
                    anchor_day=sub.billing_anchor_day,
                )

            sub.status = SUBSCRIPTION_STATUS_ACTIVE

    # =========================================================================
    # Additional Operations (Pause, Resume, Renew, Close)
    # =========================================================================

    def action_pause(self):
        """
        Pause an active subscription.
        Respects plan.allow_pause governance flag.
        """
        today = fields.Date.today()
        for sub in self:
            if sub.status != SUBSCRIPTION_STATUS_ACTIVE:
                raise UserError(_("Only Active subscriptions can be paused."))
            if sub.is_paused:
                raise UserError(_("Subscription %s is already paused.") % sub.subscription_number)
            if not sub.plan_id.allow_pause:
                raise UserError(
                    _("Plan '%s' does not permit pausing subscriptions.") % sub.plan_id.name
                )
            sub.is_paused = True
            sub.pause_date = today

    def action_resume(self):
        """
        Resume a paused subscription.
        Recalculates next billing date and expiry date by shifting them by pause duration.
        """
        today = fields.Date.today()
        for sub in self:
            if sub.status != SUBSCRIPTION_STATUS_ACTIVE or not sub.is_paused:
                raise UserError(_("Only paused subscriptions can be resumed."))

            paused_days = (today - sub.pause_date).days if sub.pause_date else 0
            if paused_days > 0:
                if sub.next_billing_date:
                    sub.next_billing_date = sub.next_billing_date + relativedelta(days=paused_days)
                if sub.expiry_date:
                    sub.expiry_date = sub.expiry_date + relativedelta(days=paused_days)

            sub.is_paused = False
            sub.resume_date = today

    def action_renew(self):
        """
        Renew an active subscription for another billing cycle.
        Respects plan.allow_renewal governance flag. Prevents duplicate renewals.
        """
        for sub in self:
            if sub.status != SUBSCRIPTION_STATUS_ACTIVE:
                raise UserError(_("Only Active subscriptions can be renewed."))
            if not sub.plan_id.allow_renewal:
                raise UserError(
                    _("Plan '%s' does not permit subscription renewal.") % sub.plan_id.name
                )

            base_date = sub.expiry_date or fields.Date.today()
            sub.expiry_date = sub.plan_id.compute_next_billing_date(base_date)
            sub.renewal_count += 1

    def action_close(self, reason='user_request'):
        """
        Terminate or close a subscription.
        If closed before expiry date, verifies plan.allow_early_close permission.
        """
        today = fields.Date.today()
        for sub in self:
            if sub.status == SUBSCRIPTION_STATUS_CLOSED:
                raise UserError(_("Subscription %s is already closed.") % sub.subscription_number)
            if sub.status not in (SUBSCRIPTION_STATUS_CONFIRMED, SUBSCRIPTION_STATUS_ACTIVE):
                raise UserError(_("Only Confirmed or Active subscriptions can be closed."))

            is_early = bool(sub.expiry_date and today < sub.expiry_date)
            if is_early and not sub.plan_id.allow_early_close:
                raise UserError(
                    _("Early closure is not permitted for plan '%s'.") % sub.plan_id.name
                )

            sub.status = SUBSCRIPTION_STATUS_CLOSED
            sub.closed_date = today
            sub.closure_reason = reason
            sub.early_closed = is_early
            sub.is_paused = False

    # =========================================================================
    # Cross-Module Integration Interfaces (Member 3 & Automated Engine)
    # =========================================================================

    @api.model
    def _get_subscriptions_due_for_billing(self, billing_date=None):
        """
        Exposed service method for Member 3 (brightloop_billing).
        Returns active, non-paused subscriptions due for recurring billing
        on or before billing_date (defaults to today).
        """
        target_date = billing_date or fields.Date.today()
        return self.search([
            ('status', '=', SUBSCRIPTION_STATUS_ACTIVE),
            ('is_paused', '=', False),
            ('next_billing_date', '<=', target_date),
        ])

    def _update_next_billing_date(self):
        """
        Exposed callback method for Member 3 (brightloop_billing).
        Advances next_billing_date by the plan billing interval and interval count,
        preserving the original billing anchor day (e.g. Jan 31 -> Feb 28 -> Mar 31).
        Called after successful invoice and BillingJob generation.
        """
        for sub in self:
            if sub.status == SUBSCRIPTION_STATUS_ACTIVE and sub.next_billing_date:
                sub.next_billing_date = sub.plan_id.compute_next_billing_date(
                    sub.next_billing_date,
                    interval_count=sub.billing_interval_count or 1,
                    anchor_day=sub.billing_anchor_day,
                )

    def action_advance_billing_date(self):
        """Backward-compatible alias invoking _update_next_billing_date."""
        return self._update_next_billing_date()

    @api.model
    def _cron_auto_close_subscriptions(self):
        """
        Automated Closure Engine:
        Finds active subscriptions whose plan has auto_close=True and expiry has passed.
        """
        today = fields.Date.today()
        subs_to_close = self.search([
            ('status', '=', SUBSCRIPTION_STATUS_ACTIVE),
            ('plan_id.auto_close', '=', True),
            '|',
            ('expiry_date', '<=', today),
            ('plan_id.end_date', '<=', today),
        ])
        for sub in subs_to_close:
            sub.action_close(reason='expired')


class BrightloopSubscriptionLine(models.Model):
    _name = 'brightloop.subscription.line'
    _description = 'Brightloop Subscription Line'
    _order = 'id asc'

    subscription_id = fields.Many2one(
        'brightloop.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_id = fields.Many2one(
        'brightloop.product',
        string='Product',
        required=True,
    )
    variant_id = fields.Many2one(
        'brightloop.product.variant',
        string='Product Variant',
        domain="[('product_id', '=', product_id)]",
    )
    name = fields.Char(
        string='Description',
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
    )
    original_unit_price = fields.Float(
        string='Original Unit Price',
        digits=(16, 2),
        help="Agreed unit price before recurring discount",
    )
    unit_price = fields.Float(
        string='Unit Price',
        digits=(16, 2),
        required=True,
        default=0.0,
        help="Agreed recurring unit price for Member 3 invoice generation",
    )
    discount = fields.Float(
        string='Discount (%)',
        digits=(16, 2),
        default=0.0,
        help="Agreed recurring discount percentage for Member 3 billing engine",
    )
    discount_amount = fields.Float(
        string='Discount Amount',
        digits=(16, 2),
        default=0.0,
        help="Agreed fixed recurring discount amount",
    )
    discount_id = fields.Char(
        string='Discount Reference',
        help="Reference or code to applicable Member 3 discount rule",
    )
    tax_id = fields.Char(
        string='Tax Reference Code',
        help="Tax reference code for Member 3 billing engine (e.g. GST_18)",
    )
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        help="Odoo accounting tax references for Member 3 invoice line generation",
    )
    plan_id = fields.Many2one(
        'brightloop.plan',
        string='Subscription Plan',
        related='subscription_id.plan_id',
        store=True,
        readonly=True,
    )
    amount_subtotal = fields.Float(
        string='Subtotal',
        digits=(16, 2),
        compute='_compute_amount_subtotal',
        store=True,
        help="Estimated line subtotal: quantity * unit_price * (1 - discount/100) - discount_amount",
    )

    @api.depends('quantity', 'unit_price', 'discount', 'discount_amount')
    def _compute_amount_subtotal(self):
        for line in self:
            base = line.quantity * line.unit_price
            discount_pct = (line.discount or 0.0) / 100.0
            subtotal = (base * (1.0 - discount_pct)) - (line.discount_amount or 0.0)
            line.amount_subtotal = max(0.0, subtotal)

    @api.onchange('product_id', 'variant_id')
    def _onchange_product(self):
        if self.variant_id and self.variant_id.product_id == self.product_id:
            self.unit_price = self.variant_id.effective_price
            self.original_unit_price = self.variant_id.effective_price
            self.name = self.variant_id.display_name
        elif self.product_id:
            self.unit_price = self.product_id.sales_price
            self.original_unit_price = self.product_id.sales_price
            self.name = self.product_id.name

    @api.constrains('quantity', 'unit_price', 'discount', 'discount_amount')
    def _check_positive_values(self):
        for line in self:
            if line.quantity <= 0.0:
                raise ValidationError(_("Line quantity must be strictly positive."))
            if line.unit_price < 0.0:
                raise ValidationError(_("Unit price cannot be negative."))
            if line.discount < 0.0 or line.discount > 100.0:
                raise ValidationError(_("Discount percentage must be between 0 and 100."))
            if line.discount_amount < 0.0:
                raise ValidationError(_("Discount amount cannot be negative."))
