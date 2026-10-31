# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Recurring Billing Engine
Owner: Member 3 (Billing, Invoice Management, Tax & Discount Lead)

Key Features:
- Find active, non-paused subscriptions due for billing via Member 2's interfaces.
- Safe per-subscription processing with PostgreSQL row locking (FOR UPDATE NOWAIT)
  with targeted 55P03 lock-conflict handling.
- Multi-company context isolation via with_company(sub.company_id).
- Expiry date validation preventing billing of expired subscriptions.
- Deterministic idempotency key calculation and duplicate billing prevention.
- Safe retry of failed billing jobs without duplicate creation.
- Native Odoo customer invoice generation (account.move) in draft state.
- Accurate line mapping, effective discount combination, and native tax assignment.
- Payment terms resolution and due date handling.
- Atomic transaction management via savepoints: rollback on failure, advance on success.
- Comprehensive ORM cache invalidation (billing_job and subscription) on rollback.
- Batch isolation: failure of one subscription never halts processing of others.
"""

import logging
from dateutil.relativedelta import relativedelta

try:
    import psycopg2
    from psycopg2 import errors as psycopg2_errors
except ImportError:
    psycopg2 = None
    psycopg2_errors = None

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.brightloop_core.models.shared_constants import (
    SUBSCRIPTION_STATUS_ACTIVE,
)

_logger = logging.getLogger(__name__)


class BrightloopBillingEngine(models.TransientModel):
    _name = 'brightloop.billing.engine'
    _description = 'Brightloop Recurring Billing Engine'

    @api.model
    def _cron_recurring_billing(self):
        """
        Scheduled action entry point for recurring subscription billing.
        Executed daily by ir.cron.
        """
        _logger.info("Starting Brightloop scheduled recurring billing run.")
        result = self.run_billing_engine()
        _logger.info(
            "Completed Brightloop recurring billing run: %d processed (%d succeeded, %d failed, %d skipped).",
            result.get('processed', 0),
            result.get('succeeded', 0),
            result.get('failed', 0),
            result.get('skipped', 0),
        )
        return result

    @api.model
    def run_billing_engine(self, billing_date=None):
        """
        Executes the recurring billing engine.
        Queries all active subscriptions due for billing on or before target billing_date,
        and processes each subscription in an isolated transaction.

        :param billing_date: Optional target date (defaults to today).
        :return: Dict containing execution summary and generated record IDs.
        """
        target_date = billing_date or fields.Date.today()
        subscription_model = self.env['brightloop.subscription']

        # Find subscriptions due for billing using Member 2's interface
        subscriptions_due = subscription_model._get_subscriptions_due_for_billing(billing_date=target_date)

        summary = {
            'target_date': target_date,
            'processed': 0,
            'succeeded': 0,
            'failed': 0,
            'skipped': 0,
            'invoice_ids': [],
            'billing_job_ids': [],
        }

        for sub in subscriptions_due:
            summary['processed'] += 1
            res = self._process_subscription_billing(sub, target_date=target_date)
            status = res.get('status')
            if status == 'done':
                summary['succeeded'] += 1
                if res.get('invoice_id'):
                    summary['invoice_ids'].append(res['invoice_id'])
                if res.get('job_id'):
                    summary['billing_job_ids'].append(res['job_id'])
            elif status == 'failed':
                summary['failed'] += 1
                if res.get('job_id'):
                    summary['billing_job_ids'].append(res['job_id'])
            elif status == 'skipped':
                summary['skipped'] += 1

        return summary

    def _lock_subscription_row(self, subscription_id):
        """
        Attempts to acquire an exclusive row lock on the subscription row using FOR UPDATE NOWAIT.
        Runs inside an isolated savepoint.
        Only catches PostgreSQL lock-not-available conflicts (error code 55P03).
        Unexpected database errors are re-raised so they are not silently treated as lock conflicts.
        """
        try:
            with self.env.cr.savepoint():
                self.env.cr.execute(
                    "SELECT id FROM brightloop_subscription WHERE id = %s FOR UPDATE NOWAIT",
                    [subscription_id],
                )
            return True
        except Exception as lock_err:
            pgcode = getattr(lock_err, 'pgcode', None)
            is_lock_conflict = (
                pgcode == '55P03'
                or (psycopg2_errors and isinstance(lock_err, psycopg2_errors.LockNotAvailable))
                or 'could not obtain lock' in str(lock_err).lower()
                or 'lock_not_available' in str(lock_err).lower()
            )
            if is_lock_conflict:
                _logger.warning(
                    "Subscription %s is currently locked by another process (skipping): %s",
                    subscription_id,
                    lock_err,
                )
                return False

            _logger.error(
                "Unexpected database error while attempting to lock subscription %s: %s",
                subscription_id,
                lock_err,
            )
            raise

    def _process_subscription_billing(self, sub, target_date=None):
        """
        Processes recurring billing for a single subscription:
        1. Excludes inactive/paused/closed subscriptions.
        2. Acquires row lock via FOR UPDATE NOWAIT with specific 55P03 conflict handling.
        3. Excludes expired subscriptions whose expiry_date is prior to period_start.
        4. Computes billing period and idempotency key.
        5. Manages Billing Job (skips completed, reuses failed/pending for retry).
        6. Atomically creates draft invoice with company context, marks job done, and advances date.
        7. Rolls back invoice and date changes if any step fails, invalidating both billing_job and sub cache.
        """
        # Guard check: Exclude inactive, paused and closed subscriptions
        if sub.status != SUBSCRIPTION_STATUS_ACTIVE or sub.is_paused:
            _logger.info("Subscription %s is not active or is paused. Skipping.", sub.id)
            return {'status': 'skipped', 'reason': 'not_active_or_paused'}

        # Row-level locking to prevent concurrent billing
        if not self._lock_subscription_row(sub.id):
            return {'status': 'skipped', 'reason': 'locked_by_concurrent_process'}

        # Re-fetch record after acquiring lock to ensure fresh database state
        sub = sub.exists()
        if not sub or sub.status != SUBSCRIPTION_STATUS_ACTIVE or sub.is_paused:
            return {'status': 'skipped', 'reason': 'state_changed_after_lock'}

        period_start = sub.next_billing_date
        if not period_start:
            return {'status': 'skipped', 'reason': 'missing_next_billing_date'}

        # Subscription expiry handling: If subscription expired before billing period starts, do not bill
        if sub.expiry_date and sub.expiry_date < period_start:
            _logger.info(
                "Subscription %s expired on %s before period start %s. Skipping.",
                sub.id,
                sub.expiry_date,
                period_start,
            )
            return {'status': 'skipped', 'reason': 'subscription_expired'}

        # Calculate billing period end: one day before next cycle date returned by compute_next_billing_date()
        next_cycle_date = sub.plan_id.compute_next_billing_date(
            period_start,
            interval_count=sub.billing_interval_count or 1,
            anchor_day=sub.billing_anchor_day,
        )
        period_end = next_cycle_date - relativedelta(days=1)

        # Deterministic idempotency key using subscription ID and billing period start
        idempotency_key = f"BILLING_{sub.id}_{period_start.isoformat()}"

        job_model = self.env['brightloop.billing.job']
        existing_job = job_model.search([('idempotency_key', '=', idempotency_key)], limit=1)

        if existing_job:
            if existing_job.state == 'done':
                _logger.info(
                    "Billing cycle %s for subscription %s already completed (Job ID %s). Skipping.",
                    period_start,
                    sub.id,
                    existing_job.id,
                )
                return {
                    'status': 'skipped',
                    'reason': 'already_completed',
                    'job_id': existing_job.id,
                }
            # Support retrying failed or pending billing jobs without creating duplicates
            billing_job = existing_job
            billing_job.write({
                'state': 'pending',
                'attempted_at': fields.Datetime.now(),
                'error_message': False,
            })
        else:
            billing_job = job_model.create({
                'subscription_id': sub.id,
                'billing_period_start': period_start,
                'billing_period_end': period_end,
                'idempotency_key': idempotency_key,
                'state': 'pending',
                'attempted_at': fields.Datetime.now(),
            })

        # Multi-company context: bind invoice creation and term resolution to subscription's company
        company = sub.company_id
        engine_company = self.with_company(company)

        # Atomic invoice generation, billing job completion, and billing date advancement
        invoice = False
        try:
            with self.env.cr.savepoint():
                invoice = engine_company._create_invoice_for_subscription(sub, period_start, period_end)
                billing_job.write({
                    'invoice_id': invoice.id,
                    'state': 'done',
                    'completed_at': fields.Datetime.now(),
                    'error_message': False,
                })
                # Advance next_billing_date using Member 2's interface
                sub._update_next_billing_date()

            return {
                'status': 'done',
                'job_id': billing_job.id,
                'invoice_id': invoice.id if invoice else False,
            }
        except Exception as exc:
            _logger.exception(
                "Billing failed for subscription %s (period %s): %s",
                sub.id,
                period_start,
                exc,
            )
            # Inner savepoint rolled back invoice creation and subscription date changes.
            # Invalidate ORM cache for both billing_job and sub so in-memory records
            # immediately reflect the committed database state rather than rolled-back savepoint values.
            billing_job.invalidate_recordset()
            sub.invalidate_recordset()
            # Record error in Billing Job using an isolated savepoint.
            try:
                with self.env.cr.savepoint():
                    billing_job.write({
                        'state': 'failed',
                        'error_message': str(exc),
                        'invoice_id': False,
                    })
            except Exception as job_err:
                _logger.error(
                    "Failed to record failure state on billing job %s: %s",
                    billing_job.id,
                    job_err,
                )

            return {
                'status': 'failed',
                'job_id': billing_job.id,
                'error': str(exc),
            }

    @api.model
    def _calculate_effective_discount(self, unit_price, quantity, percentage_discount, fixed_discount):
        """
        Combines percentage and fixed discounts into a single effective percentage.

        Formula:
            gross = quantity * unit_price
            net_before_fixed = unit_price * (1 - percentage_discount / 100)
            net_unit_price = max(0, net_before_fixed - fixed_discount / quantity)
            effective_discount = 100 * (1 - net_unit_price / unit_price)

        Handles zero-priced lines separately and clamps between 0.0 and 100.0.
        """
        if unit_price <= 0.0 or quantity <= 0.0:
            return 0.0

        pct = float(percentage_discount or 0.0)
        fixed = float(fixed_discount or 0.0)

        net_before_fixed = unit_price * (1.0 - (pct / 100.0))
        net_unit_price = max(0.0, net_before_fixed - (fixed / quantity))
        effective_discount = 100.0 * (1.0 - (net_unit_price / unit_price))

        return max(0.0, min(100.0, round(effective_discount, 4)))

    def _resolve_payment_terms_and_due_date(self, sub, invoice_date):
        """
        Resolves payment term and due date from the subscription's payment_terms Char field.
        Evaluates within the subscription's company context.
        If it matches an existing account.payment.term, use that record.
        If it represents immediate payment or no matching term exists, set invoice_date_due = invoice_date.
        """
        raw_term = (sub.payment_terms or '').strip()
        term_model = self.env['account.payment.term'].with_company(sub.company_id)

        payment_term = False
        if raw_term:
            payment_term = term_model.search([
                ('name', '=ilike', raw_term),
                ('company_id', 'in', [False, sub.company_id.id]),
            ], limit=1)

        is_immediate = not raw_term or raw_term.lower() in (
            'immediate',
            'immediate payment',
            'immediate_payment',
            'cash',
        )

        vals = {}
        if payment_term:
            vals['invoice_payment_term_id'] = payment_term.id
            if is_immediate:
                vals['invoice_date_due'] = invoice_date
        else:
            vals['invoice_date_due'] = invoice_date

        return vals

    def _create_invoice_for_subscription(self, sub, period_start, period_end):
        """
        Generates a native Odoo customer invoice (account.move) in draft state.
        Executes within the subscription's company context via with_company.
        Required fields:
        - move_type = 'out_invoice'
        - partner_id
        - subscription_id
        - company_id
        - invoice_date
        - invoice_date_due or invoice_payment_term_id
        - invoice_line_ids

        Maps subscription lines to native invoice lines without assigning brightloop.product to native product_id.
        Applies effective combined discount and native accounting taxes filtered by company.
        """
        if not sub.line_ids:
            raise UserError(_("Subscription %s has no subscription lines to bill.") % sub.subscription_number)

        company = sub.company_id
        invoice_date = period_start

        invoice_line_commands = []
        for line in sub.line_ids:
            if line.quantity <= 0:
                continue

            # Determine line description
            line_name = line.name
            if not line_name:
                if line.variant_id:
                    v_name = line.variant_id.display_name or line.variant_id.name or ''
                    p_name = line.product_id.name or ''
                    line_name = f"{p_name} ({v_name})" if v_name else p_name
                elif line.product_id:
                    line_name = line.product_id.name
                else:
                    line_name = _("Subscription Item")

            effective_discount = self._calculate_effective_discount(
                unit_price=line.unit_price,
                quantity=line.quantity,
                percentage_discount=line.discount,
                fixed_discount=line.discount_amount,
            )

            line_vals = {
                'name': line_name,
                'quantity': line.quantity,
                'price_unit': line.unit_price,
                'discount': effective_discount,
                # Do not assign brightloop.product to native product_id. Leave native product_id unset.
                'product_id': False,
            }

            if line.tax_ids:
                # Ensure taxes match the subscription's company
                company_taxes = line.tax_ids.filtered(lambda t: not t.company_id or t.company_id == company)
                if company_taxes:
                    line_vals['tax_ids'] = [fields.Command.set(company_taxes.ids)]

            invoice_line_commands.append(fields.Command.create(line_vals))

        if not invoice_line_commands:
            raise UserError(_("Subscription %s has no positive quantity lines.") % sub.subscription_number)

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': sub.partner_id.id,
            'subscription_id': sub.id,
            'company_id': company.id,
            'currency_id': company.currency_id.id,
            'invoice_date': invoice_date,
            'invoice_line_ids': invoice_line_commands,
        }

        # Resolve payment terms and due date
        term_vals = self._resolve_payment_terms_and_due_date(sub, invoice_date)
        invoice_vals.update(term_vals)

        # Draft customer invoice created in the subscription's company context (never auto-posted)
        invoice = self.env['account.move'].with_company(company).create(invoice_vals)
        return invoice
