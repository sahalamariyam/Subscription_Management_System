# -*- coding: utf-8 -*-
{
    'name': 'Brightloop Subscription Management',
    'version': '18.0.1.0.0',
    'category': 'Sales/Subscription',
    'summary': 'Products, Product Variants, Plans, Quotation Templates and Subscription Lifecycle Management',
    'description': """
Brightloop Subscription Management System - Commercial Subscription Engine
==========================================================================
Owned by: Member 2 (Product, Plan, Quotation & Subscription Lifecycle Lead)

Key Features:
- Product and variant management with configurable price adjustments
- Subscription plan management with daily, weekly, monthly, and yearly intervals
- Plan governance permissions: auto-close, early close, pause, renewal
- Quotation templates and customer quotation generation
- Full subscription lifecycle: Draft -> Quotation -> Confirmed -> Active -> Closed
- Pause/resume with billing date recalculation and duplicate-renewal prevention
- Secure integration interfaces for Member 3 (Billing/Invoices) and Member 4 (Finance/Payments)
    """,
    'author': 'Brightloop Team (Member 2 - Product & Subscription Lead)',
    'website': 'https://github.com/sahalamariyam/Subscription_Management_System',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'portal',
        'brightloop_core',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/subscription_security.xml',
        'data/sequence_data.xml',
        'views/menu_views.xml',
        'views/product_views.xml',
        'views/plan_views.xml',
        'views/quotation_template_views.xml',
        'views/subscription_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
