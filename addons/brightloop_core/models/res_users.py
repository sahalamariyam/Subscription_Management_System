# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — User Identity & Security Extensions
Owner: Member 1 (Platform Foundation, Authentication & Security Lead)

Enforces:
1. Strict server-side password policy (length > 8, uppercase, lowercase, special char).
2. Administrator-only staff account creation.
3. Server-side privilege escalation prevention (staff cannot promote self or others).
4. Safe preservation of Odoo native authentication, hashing, and portal signup flows.
"""

import re
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.fields import Command
from .shared_constants import ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER, ROLE_SELECTION


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Canonical Brightloop Role (computed from actual Odoo groups)
    brightloop_role = fields.Selection(
        selection=ROLE_SELECTION,
        string='Brightloop Role',
        compute='_compute_brightloop_role',
        store=False,
        help="Canonical role for Brightloop platform permissions",
    )

    is_brightloop_admin = fields.Boolean(
        string='Is Brightloop Admin',
        compute='_compute_brightloop_role',
        store=False,
    )

    is_brightloop_staff = fields.Boolean(
        string='Is Brightloop Staff',
        compute='_compute_brightloop_role',
        store=False,
    )

    is_brightloop_customer = fields.Boolean(
        string='Is Brightloop Customer',
        compute='_compute_brightloop_role',
        store=False,
    )

    @api.depends('groups_id')
    def _compute_brightloop_role(self):
        admin_group = self.env.ref('brightloop_core.group_brightloop_admin', raise_if_not_found=False)
        staff_group = self.env.ref('brightloop_core.group_brightloop_staff', raise_if_not_found=False)
        customer_group = self.env.ref('brightloop_core.group_brightloop_customer', raise_if_not_found=False)

        for user in self:
            is_adm = (admin_group and admin_group in user.groups_id) or user.id == SUPERUSER_ID
            is_stf = staff_group and staff_group in user.groups_id
            is_cust = customer_group and customer_group in user.groups_id

            user.is_brightloop_admin = is_adm
            user.is_brightloop_staff = is_stf
            user.is_brightloop_customer = is_cust

            if is_adm:
                user.brightloop_role = ROLE_ADMIN
            elif is_stf:
                user.brightloop_role = ROLE_STAFF
            elif is_cust:
                user.brightloop_role = ROLE_CUSTOMER
            else:
                user.brightloop_role = False

    # =========================================================================
    # Role Verification Helpers
    # =========================================================================

    def _is_brightloop_admin(self):
        """Check whether the current user is an authorized Brightloop administrator."""
        self.ensure_one()
        if self._is_superuser() or self.env.is_admin():
            return True
        return self.has_group('brightloop_core.group_brightloop_admin')

    def _is_brightloop_staff(self):
        """Check whether the current user is a Brightloop staff member."""
        self.ensure_one()
        return self.has_group('brightloop_core.group_brightloop_staff')

    def _is_brightloop_customer(self):
        """Check whether the current user is a Brightloop customer."""
        self.ensure_one()
        return self.has_group('brightloop_core.group_brightloop_customer')

    @api.model
    def _get_privileged_group_ids(self):
        """Return the set of group IDs considered privileged in Brightloop."""
        refs = [
            'brightloop_core.group_brightloop_admin',
            'brightloop_core.group_brightloop_staff',
            'base.group_user',
            'base.group_erp_manager',
            'base.group_system',
        ]
        gids = set()
        for ref in refs:
            grp = self.env.ref(ref, raise_if_not_found=False)
            if grp:
                gids.add(grp.id)
        return gids

    @api.model
    def _extract_added_group_ids(self, commands):
        """Extract all group IDs being added or set from an ORM command list."""
        added_ids = set()
        if not commands:
            return added_ids
        for cmd in commands:
            if not isinstance(cmd, (list, tuple)) or len(cmd) < 2:
                continue
            op = cmd[0]
            if op == 4 or op == Command.LINK:
                added_ids.add(cmd[1])
            elif (op == 6 or op == Command.SET) and len(cmd) >= 3:
                added_ids.update(cmd[2] or [])
        return added_ids

    # =========================================================================
    # Server-Side Password Policy Enforcement
    # =========================================================================

    @api.model
    def _validate_password_policy(self, password):
        """
        Enforce Brightloop Password Security Requirements:
        - Strictly more than 8 characters (len > 8)
        - At least one uppercase letter ([A-Z])
        - At least one lowercase letter ([a-z])
        - At least one special character ([^A-Za-z0-9])

        Raises ValidationError if any condition is not met.
        """
        if not password:
            raise ValidationError(_("Password cannot be empty."))
        if len(password) <= 8:
            raise ValidationError(_("Password must be more than 8 characters long."))
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_("Password must contain at least one uppercase letter."))
        if not re.search(r'[a-z]', password):
            raise ValidationError(_("Password must contain at least one lowercase letter."))
        if not re.search(r'[^A-Za-z0-9]', password):
            raise ValidationError(_("Password must contain at least one special character."))
        return True

    def _set_password(self):
        """
        Intercept all password assignments (create, write, reset, signup)
        to validate password complexity before native Odoo hashing.
        """
        for user in self:
            if user.password:
                self._validate_password_policy(user.password)
        return super()._set_password()

    def _change_password(self, new_passwd):
        """Validate password policy on interactive password change."""
        if new_passwd:
            self._validate_password_policy(new_passwd)
        return super()._change_password(new_passwd)

    # =========================================================================
    # Server-Side Access Control & Privilege Escalation Prevention
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """
        Enforce Admin-Only Staff Account Creation.
        Non-administrators cannot create accounts with staff/admin privileges.
        """
        current_user = self.env.user
        is_admin = (
            self.env.uid == SUPERUSER_ID
            or (current_user and current_user._is_brightloop_admin())
        )
        privileged_ids = self._get_privileged_group_ids()

        for vals in vals_list:
            if not is_admin:
                if 'groups_id' in vals:
                    added_groups = self._extract_added_group_ids(vals['groups_id'])
                    if added_groups & privileged_ids:
                        raise AccessError(_("Only Brightloop administrators may create staff or administrator accounts."))
                if vals.get('share') is False:
                    raise AccessError(_("Only Brightloop administrators may create internal staff accounts."))

        return super().create(vals_list)

    def write(self, values):
        """
        Prevent unauthorized users from promoting themselves or others,
        or modifying security group memberships.
        """
        current_user = self.env.user
        is_admin = (
            self.env.uid == SUPERUSER_ID
            or (current_user and current_user._is_brightloop_admin())
        )

        if 'groups_id' in values and not is_admin:
            privileged_ids = self._get_privileged_group_ids()
            added_groups = self._extract_added_group_ids(values['groups_id'])
            if added_groups & privileged_ids:
                raise AccessError(_("Only Brightloop administrators may assign staff or administrator roles."))
            raise AccessError(_("Only Brightloop administrators may modify user security groups."))

        return super().write(values)
