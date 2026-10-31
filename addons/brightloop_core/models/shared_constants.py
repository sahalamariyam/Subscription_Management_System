# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System - Shared Architecture Constants
Owner: Member 1 (Platform Foundation, Authentication & Integration Lead)

These canonical values establish the shared contract across:
- brightloop_core (Platform & Identity - Member 1)
- brightloop_subscription (Products & Lifecycle - Member 2)
- brightloop_billing (Billing & Invoices - Member 3)
- brightloop_finance (Payments & Dashboard - Member 4)
"""

# =========================================================================
# Canonical User & Access Roles
# =========================================================================
ROLE_ADMIN = 'admin'
ROLE_STAFF = 'staff'
ROLE_CUSTOMER = 'customer'

ROLE_SELECTION = [
    (ROLE_ADMIN, 'Administrator'),
    (ROLE_STAFF, 'Staff Member'),
    (ROLE_CUSTOMER, 'Customer'),
]

VALID_ROLES = {ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER}

# =========================================================================
# Subscription Lifecycle Statuses
# =========================================================================
SUBSCRIPTION_STATUS_DRAFT = 'draft'
SUBSCRIPTION_STATUS_QUOTATION = 'quotation'
SUBSCRIPTION_STATUS_CONFIRMED = 'confirmed'
SUBSCRIPTION_STATUS_ACTIVE = 'active'
SUBSCRIPTION_STATUS_CLOSED = 'closed'

SUBSCRIPTION_STATUS_SELECTION = [
    (SUBSCRIPTION_STATUS_DRAFT, 'Draft'),
    (SUBSCRIPTION_STATUS_QUOTATION, 'Quotation'),
    (SUBSCRIPTION_STATUS_CONFIRMED, 'Confirmed'),
    (SUBSCRIPTION_STATUS_ACTIVE, 'Active'),
    (SUBSCRIPTION_STATUS_CLOSED, 'Closed'),
]

VALID_SUBSCRIPTION_STATUSES = {
    SUBSCRIPTION_STATUS_DRAFT,
    SUBSCRIPTION_STATUS_QUOTATION,
    SUBSCRIPTION_STATUS_CONFIRMED,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_CLOSED,
}

# =========================================================================
# Invoice Lifecycle Statuses
# =========================================================================
INVOICE_STATUS_DRAFT = 'draft'
INVOICE_STATUS_CONFIRMED = 'confirmed'
INVOICE_STATUS_PAID = 'paid'

INVOICE_STATUS_SELECTION = [
    (INVOICE_STATUS_DRAFT, 'Draft'),
    (INVOICE_STATUS_CONFIRMED, 'Confirmed'),
    (INVOICE_STATUS_PAID, 'Paid'),
]

VALID_INVOICE_STATUSES = {
    INVOICE_STATUS_DRAFT,
    INVOICE_STATUS_CONFIRMED,
    INVOICE_STATUS_PAID,
}

# =========================================================================
# Billing Intervals
# =========================================================================
BILLING_INTERVAL_DAILY = 'daily'
BILLING_INTERVAL_WEEKLY = 'weekly'
BILLING_INTERVAL_MONTHLY = 'monthly'
BILLING_INTERVAL_YEARLY = 'yearly'

BILLING_INTERVAL_SELECTION = [
    (BILLING_INTERVAL_DAILY, 'Daily'),
    (BILLING_INTERVAL_WEEKLY, 'Weekly'),
    (BILLING_INTERVAL_MONTHLY, 'Monthly'),
    (BILLING_INTERVAL_YEARLY, 'Yearly'),
]

VALID_BILLING_INTERVALS = {
    BILLING_INTERVAL_DAILY,
    BILLING_INTERVAL_WEEKLY,
    BILLING_INTERVAL_MONTHLY,
    BILLING_INTERVAL_YEARLY,
}

