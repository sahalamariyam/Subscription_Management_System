# -*- coding: utf-8 -*-
"""
Brightloop Subscription Management System — Authentication & Signup Controllers
Owner: Member 1 (Platform Foundation, Authentication & Security Lead)

Extends native Odoo auth_signup to provide:
1. Anti-enumeration protections on password reset requests.
2. Server-side email format validation for public requests.
3. Clean error handling preserving strict password policy feedback.
"""

import logging
import re
import werkzeug

from odoo import http, _
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome

_logger = logging.getLogger(__name__)


class BrightloopAuthSignupHome(AuthSignupHome):

    @http.route('/web/reset_password', type='http', auth='public', website=True, sitemap=False)
    def web_auth_reset_password(self, *args, **kw):
        """
        Secure password reset handler with anti-enumeration protection.

        Standard Odoo behavior raises 'No account found for this login', which
        allows unauthenticated attackers to enumerate valid customer emails.
        This override presents a uniform generic confirmation message whether
        the email exists or not, while triggering the native reset email for
        legitimate accounts.
        """
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('reset_password_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            # Case 1: Initial password reset request (no token in query/form)
            if not qcontext.get('token'):
                login = qcontext.get('login') or ''
                login = login.strip()
                if not login:
                    qcontext['error'] = _("Please provide a valid email address.")
                elif not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', login):
                    qcontext['error'] = _("Please provide a valid email address.")
                else:
                    try:
                        request.env['res.users'].sudo().reset_password(login)
                    except Exception as e:
                        # Log internally for diagnostics, but do not leak existence to user
                        _logger.info("Password reset requested for login: %s (%s)", login, e)

                    # Uniform message to prevent email enumeration
                    qcontext['message'] = _("If an account exists for this email address, password reset instructions have been sent.")

                response = request.render('auth_signup.reset_password', qcontext)
                response.headers['X-Frame-Options'] = 'SAMEORIGIN'
                response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
                return response

        # Case 2: Token-based reset or GET requests delegate to native Odoo handler
        return super().web_auth_reset_password(*args, **kw)
