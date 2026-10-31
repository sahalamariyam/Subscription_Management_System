# -*- coding: utf-8 -*-
from ast import literal_eval
from odoo.fields import Command
from . import models
from . import controllers


def post_init_hook(env):
    """Ensure B2C signup, reset password, and template portal user group are configured."""
    IrConfigParam = env['ir.config_parameter'].sudo()
    IrConfigParam.set_param('auth_signup.invitation_scope', 'b2c')
    IrConfigParam.set_param('auth_signup.reset_password', 'True')

    template_user_id = literal_eval(IrConfigParam.get_param('base.template_portal_user_id', 'False'))
    if template_user_id:
        tpl = env['res.users'].sudo().browse(template_user_id)
        cust_group = env.ref('brightloop_core.group_brightloop_customer', raise_if_not_found=False)
        if cust_group and cust_group not in tpl.groups_id:
            tpl.write({'groups_id': [Command.link(cust_group.id)]})

