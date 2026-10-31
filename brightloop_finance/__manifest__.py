# -*- coding: utf-8 -*-
{
    'name': 'Brightloop Finance',
    'version': '18.0.1.0.0',
    'summary': 'Payment management, financial dashboard and reporting for Brightloop subscriptions',
    'description': """
        Brightloop Finance Module
        =========================
        Owned by: Member 4
        Odoo version: 18.0 Community (confirmed)

        Provides:
        - Payment recording (manual and gateway)
        - Invoice payment allocation (partial, multiple, overpayment)
        - Outstanding and overdue balance tracking
        - Financial dashboard with filters
        - Excel (xlsx) export for reporting

        Invoice model: account.move (confirmed with Member 3, 2026-10-31)
          move_type = 'out_invoice' (customer invoices only)
        Subscription model: brightloop.subscription (confirmed with Member 2, 2026-10-31)
    """,
    'author': 'Brightloop Team - Member 4',
    'category': 'Accounting/Finance',
    'license': 'LGPL-3',

    # Odoo 16/17 compatible
    'depends': [
        'base',
        'mail',
        'account',          # Odoo 18 native — account.move is the invoice model
        'brightloop_billing',   # Member 3 — extends account.move with subscription_id ✅
        'brightloop_core',  # Member 1 shared constants — add when available
    ],

    'data': [
        # Security — load first
        'security/security_groups.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence_data.xml',
        'data/payment_method_data.xml',

        # Views
        'views/payment_views.xml',
        'views/invoice_payment_views.xml',
        'views/dashboard_views.xml',

        # Wizards
        'wizard/payment_wizard_views.xml',

        # Reports / Export
        'report/finance_export_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'brightloop_finance/static/src/dashboard.js',
            'brightloop_finance/static/src/dashboard.xml',
            'brightloop_finance/static/src/dashboard.scss',
        ],
    },

    'installable': True,
    'application': False,
    'auto_install': False,

    # installable: True once brightloop_billing and brightloop_core are merged to main
    'external_dependencies': {},
}
