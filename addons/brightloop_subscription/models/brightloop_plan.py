# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Subscription Plan Model
Owner: Member 2 (Product, Plan, Quotation & Subscription Lifecycle Lead)

Implements:
- Subscription plans with daily, weekly, monthly, and yearly billing intervals.
- Plan pricing and minimum subscriber quantity rules.
- Availability validity window (start_date, end_date).
- Active business governance permissions:
  * auto_close: Automatic closure on termination condition.
  * allow_early_close: Permission to terminate before term.
  * allow_pause: Permission to pause billing.
  * allow_renewal: Permission to renew subscriptions.
"""

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.brightloop_core.models.shared_constants import (
    BILLING_INTERVAL_SELECTION,
    BILLING_INTERVAL_DAILY,
    BILLING_INTERVAL_WEEKLY,
    BILLING_INTERVAL_MONTHLY,
    BILLING_INTERVAL_YEARLY,
)


class BrightloopPlan(models.Model):
    _name = 'brightloop.plan'
    _description = 'Brightloop Subscription Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(
        string='Plan Name',
        required=True,
        tracking=True,
        help="Display name of the subscription plan (e.g. Starter Monthly, Enterprise Annual)",
    )
    billing_price = fields.Float(
        string='Billing Price',
        digits=(16, 2),
        required=True,
        default=0.0,
        tracking=True,
        help="Base recurring subscription price for this plan",
    )
    billing_interval = fields.Selection(
        selection=BILLING_INTERVAL_SELECTION,
        string='Billing Interval',
        default=BILLING_INTERVAL_MONTHLY,
        required=True,
        tracking=True,
        help="Recurring billing cadence: Daily, Weekly, Monthly, or Yearly",
    )
    minimum_quantity = fields.Integer(
        string='Minimum Quantity',
        default=1,
        required=True,
        tracking=True,
        help="Minimum subscription seats or product quantity required for this plan",
    )
    start_date = fields.Date(
        string='Availability Start Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="Date from which the plan can be offered to customers",
    )
    end_date = fields.Date(
        string='Availability End Date',
        tracking=True,
        help="Date until which the plan is available. Leave empty for open-ended plans",
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archived plans cannot be assigned to new quotations or subscriptions",
    )

    # =========================================================================
    # Plan Governance Permissions (Enforce Real Business Rules)
    # =========================================================================
    auto_close = fields.Boolean(
        string='Automatic Closure',
        default=False,
        tracking=True,
        help="When enabled, subscriptions under this plan will automatically close when the plan ends or reaches term",
    )
    allow_early_close = fields.Boolean(
        string='Allow Early Closure',
        default=True,
        tracking=True,
        help="Permit customers or staff to terminate subscriptions before the scheduled expiry date",
    )
    allow_pause = fields.Boolean(
        string='Allow Pause',
        default=True,
        tracking=True,
        help="Permit subscriptions on this plan to be paused and resumed",
    )
    allow_renewal = fields.Boolean(
        string='Allow Renewal',
        default=True,
        tracking=True,
        help="Permit subscriptions on this plan to be renewed",
    )

    # =========================================================================
    # Validation Constraints
    # =========================================================================
    @api.constrains('billing_price')
    def _check_billing_price(self):
        for plan in self:
            if plan.billing_price < 0.0:
                raise ValidationError(_("Billing price cannot be negative."))

    @api.constrains('minimum_quantity')
    def _check_minimum_quantity(self):
        for plan in self:
            if plan.minimum_quantity < 1:
                raise ValidationError(_("Minimum quantity must be at least 1."))

    @api.constrains('start_date', 'end_date')
    def _check_availability_dates(self):
        for plan in self:
            if plan.start_date and plan.end_date and plan.end_date < plan.start_date:
                raise ValidationError(_("Availability End Date cannot be earlier than Availability Start Date."))

    # =========================================================================
    # Business Logic Helpers
    # =========================================================================
    def is_available_on(self, target_date=None):
        """Check if plan is within its active availability window on target_date."""
        self.ensure_one()
        check_date = target_date or fields.Date.today()
        if self.start_date and check_date < self.start_date:
            return False
        if self.end_date and check_date > self.end_date:
            return False
        return self.active

    def compute_next_billing_date(self, current_date):
        """
        Compute the next billing date based on the plan's billing interval.
        Canonical intervals: daily, weekly, monthly, yearly.
        """
        self.ensure_one()
        if not current_date:
            return False

        if self.billing_interval == BILLING_INTERVAL_DAILY:
            return current_date + relativedelta(days=1)
        elif self.billing_interval == BILLING_INTERVAL_WEEKLY:
            return current_date + relativedelta(weeks=1)
        elif self.billing_interval == BILLING_INTERVAL_MONTHLY:
            return current_date + relativedelta(months=1)
        elif self.billing_interval == BILLING_INTERVAL_YEARLY:
            return current_date + relativedelta(years=1)
        return current_date + relativedelta(months=1)
