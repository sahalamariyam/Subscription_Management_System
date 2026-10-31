# -*- coding: utf-8 -*-
{
    'name': 'Brightloop Core Platform',
    'version': '18.0.1.0.0',
    'category': 'Platform',
    'summary': 'Platform foundation, shared constants, and identity management for Brightloop',
    'description': """
Brightloop Subscription Management System - Platform Foundation
===============================================================
Central integration module for the Brightloop platform.
Maintains canonical roles (Admin, Staff, Customer), shared status enums,
strict password policies, and customer data isolation rules.

Workstream Ownership: Member 1 (Platform Foundation, Authentication & Security Lead)
    """,
    'author': 'Brightloop Team (Member 1 - Foundation Lead)',
    'website': 'https://github.com/sahalamariyam/Subscription_Management_System',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'portal',
    ],
    'data': [
        'security/brightloop_security.xml',
        'security/ir.model.access.csv',
        'security/customer_rules.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
