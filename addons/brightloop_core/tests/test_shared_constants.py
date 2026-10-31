# -*- coding: utf-8 -*-
import unittest
from odoo.addons.brightloop_core.models import shared_constants


class TestSharedConstants(unittest.TestCase):
    """Test that canonical architecture constants match project requirements."""

    def test_canonical_roles(self):
        expected_roles = {'admin', 'staff', 'customer'}
        self.assertEqual(shared_constants.VALID_ROLES, expected_roles)
        selection_keys = {key for key, _ in shared_constants.ROLE_SELECTION}
        self.assertEqual(selection_keys, expected_roles)

    def test_subscription_statuses(self):
        expected_statuses = {'draft', 'quotation', 'confirmed', 'active', 'closed'}
        self.assertEqual(shared_constants.VALID_SUBSCRIPTION_STATUSES, expected_statuses)
        selection_keys = {key for key, _ in shared_constants.SUBSCRIPTION_STATUS_SELECTION}
        self.assertEqual(selection_keys, expected_statuses)

    def test_invoice_statuses(self):
        expected_statuses = {'draft', 'confirmed', 'paid'}
        self.assertEqual(shared_constants.VALID_INVOICE_STATUSES, expected_statuses)
        selection_keys = {key for key, _ in shared_constants.INVOICE_STATUS_SELECTION}
        self.assertEqual(selection_keys, expected_statuses)

    def test_billing_intervals(self):
        expected_intervals = {'daily', 'weekly', 'monthly', 'yearly'}
        self.assertEqual(shared_constants.VALID_BILLING_INTERVALS, expected_intervals)
        selection_keys = {key for key, _ in shared_constants.BILLING_INTERVAL_SELECTION}
        self.assertEqual(selection_keys, expected_intervals)

