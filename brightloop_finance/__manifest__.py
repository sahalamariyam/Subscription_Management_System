# -*- coding: utf-8 -*-
{
    'name': 'Brightloop Finance',
    'version': '1.0.0',
    'summary': 'Payment management, financial dashboard and reporting for Brightloop subscriptions',
    'description': """
        Brightloop Finance Module
        =========================
        Owned by: Member 4

        Provides:
        - Payment recording (manual and gateway)
        - Invoice payment allocation (partial, multiple, overpayment)
        - Outstanding and overdue balance tracking
        - Financial dashboard with filters
        - Excel (xlsx) export for reporting

        Reads invoice data from: brightloop_billing (Member 3)
        Reads subscription/customer data via shared interfaces (Member 1)
    """,
    'author': 'Brightloop Team - Member 4',
    'category': 'Accounting/Finance',
    'license': 'LGPL-3',

    # Odoo 16/17 compatible
    'depends': [
        'base',
        'mail',          # chatter/logging on payment records
        'brightloop_billing',  # Member 3 — invoice model (coordinate before activating)
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

    # Change to False once Member 3's module is confirmed installed
    # and remove this comment before final submission
    'external_dependencies': {},
}
