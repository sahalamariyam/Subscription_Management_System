{
    'name': 'Brightloop Billing',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Subscriptions',
    'summary': 'Recurring billing, invoice generation, taxes and discounts',
    'description': """
Brightloop Billing Module
=========================
Owned by: Member 3

Features:
- Recurring subscription billing engine
- Native Odoo customer invoice generation
- Billing job tracking and idempotency
- Automatic billing date advancement
- Recurring discounts and accounting taxes
- Scheduled billing execution (daily cron)
- Finance module integration
    """,
    'author': 'Brightloop Team - Member 3',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'mail',
        'brightloop_core',
        'brightloop_subscription',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
