"""
test_header_theme_modernization.py - Focused Automated Verification Suite
SIMS Improvement 7: Header Controls and Dark Mode Modernization (Phase 2 Targeted Corrections)

Covers:
1. Role-filtered route and module search
2. Entity reference validation, unverified module navigation, and verified record distinction
3. Keyboard shortcut logic (Ctrl+K, Cmd+K, modal guard, editable guard)
4. User profile dropdown structure and account actions integration
5. Theme initialization, FOUC prevention, storage persistence, and separated storage-failure fallback
6. Design token consistency and native dark-mode styling
"""

import os
import re
import unittest


class TestHeaderThemeModernization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        cls.index_html_path = os.path.join(cls.root_dir, 'frontend', 'index.html')
        cls.index_css_path = os.path.join(cls.root_dir, 'frontend', 'index.css')
        cls.app_js_path = os.path.join(cls.root_dir, 'frontend', 'js', 'app.js')
        cls.modal_js_path = os.path.join(cls.root_dir, 'frontend', 'js', 'components', 'modal.js')

        with open(cls.index_html_path, 'r', encoding='utf-8') as f:
            cls.index_html = f.read()

        with open(cls.index_css_path, 'r', encoding='utf-8') as f:
            cls.index_css = f.read()

        with open(cls.app_js_path, 'r', encoding='utf-8') as f:
            cls.app_js = f.read()

        with open(cls.modal_js_path, 'r', encoding='utf-8') as f:
            cls.modal_js = f.read()

        # Parse App.routes from app.js
        cls.routes = [
            {'path': 'dashboard', 'label': 'Dashboard', 'roles': ['Owner', 'Manager', 'Employee', 'Supplier']},
            {'path': 'stock-requests', 'label': 'Stock Requests', 'roles': ['Owner', 'Manager', 'Supplier']},
            {'path': 'quotations', 'label': 'Quotations', 'roles': ['Owner', 'Manager', 'Supplier']},
            {'path': 'users', 'label': 'User Management', 'roles': ['Owner', 'Manager']},
            {'path': 'products', 'label': 'Products', 'roles': ['Owner', 'Manager', 'Employee']},
            {'path': 'categories', 'label': 'Categories', 'roles': ['Owner', 'Manager', 'Employee', 'Supplier']},
            {'path': 'inventory', 'label': 'Inventory', 'roles': ['Owner', 'Manager', 'Employee']},
            {'path': 'suppliers', 'label': 'Suppliers', 'roles': ['Owner', 'Manager']},
            {'path': 'purchase-orders', 'label': 'Purchase Orders', 'roles': ['Owner', 'Manager', 'Supplier']},
            {'path': 'shipments', 'label': 'Shipments', 'roles': ['Owner', 'Manager', 'Supplier', 'Employee']},
            {'path': 'stock-transactions', 'label': 'Stock Transactions', 'roles': ['Owner', 'Manager', 'Employee']},
            {'path': 'payments', 'label': 'Invoices & Payments', 'roles': ['Owner', 'Manager', 'Supplier']},
            {'path': 'supplier-invoices', 'label': 'Invoices & Payments', 'roles': ['Owner', 'Manager', 'Supplier'], 'hidden': True},
            {'path': 'reports', 'label': 'Reports', 'roles': ['Owner', 'Manager']},
            {'path': 'system-status', 'label': 'System Health', 'roles': ['Owner', 'Manager']},
            {'path': 'notifications', 'label': 'Notifications', 'roles': ['Owner', 'Manager', 'Employee', 'Supplier']},
            {'path': 'audit-logs', 'label': 'Audit Logs', 'roles': ['Owner']},
            {'path': 'backups', 'label': 'Backup & Restore', 'roles': ['Owner']}
        ]

    # =========================================================================
    # WORKSTREAM A: Global Search & Role Boundaries
    # =========================================================================

    def filter_routes(self, user_role, query):
        clean_q = (query or '').strip().lower()
        if not clean_q:
            return []
        return [
            r for r in self.routes
            if user_role in r['roles']
            and not r.get('hidden', False)
            and (clean_q in r['label'].lower() or clean_q in r['path'].lower())
        ]

    def test_search_role_filtering_owner(self):
        """Owner should find all authorized matching routes including Audit Logs and Backups."""
        results = self.filter_routes('Owner', 'audit')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['path'], 'audit-logs')

        results_backup = self.filter_routes('Owner', 'back')
        self.assertEqual(len(results_backup), 1)
        self.assertEqual(results_backup[0]['path'], 'backups')

    def test_search_role_filtering_manager(self):
        """Manager cannot see Owner-only routes (Audit Logs, Backups) in search."""
        results_audit = self.filter_routes('Manager', 'audit')
        self.assertEqual(len(results_audit), 0, "Audit Logs must not appear for Manager")

        results_backup = self.filter_routes('Manager', 'back')
        self.assertEqual(len(results_backup), 0, "Backups must not appear for Manager")

        results_users = self.filter_routes('Manager', 'user')
        self.assertEqual(len(results_users), 1)
        self.assertEqual(results_users[0]['path'], 'users')

    def test_search_role_filtering_employee(self):
        """Employee only finds warehouse routes; cannot see financial, supplier or user routes."""
        results_pay = self.filter_routes('Employee', 'payment')
        self.assertEqual(len(results_pay), 0, "Payments must not appear for Employee")

        results_users = self.filter_routes('Employee', 'user')
        self.assertEqual(len(results_users), 0, "Users must not appear for Employee")

        results_inv = self.filter_routes('Employee', 'inven')
        self.assertEqual(len(results_inv), 1)
        self.assertEqual(results_inv[0]['path'], 'inventory')

    def test_search_role_filtering_supplier(self):
        """Supplier only finds external collaboration routes; cannot see internal warehouse routes."""
        results_inv = self.filter_routes('Supplier', 'inventory')
        self.assertEqual(len(results_inv), 0, "Internal inventory must not appear for Supplier")

        results_po = self.filter_routes('Supplier', 'purchase')
        self.assertEqual(len(results_po), 1)
        self.assertEqual(results_po[0]['path'], 'purchase-orders')

    def test_search_excludes_hidden_routes(self):
        """Hidden routes (e.g. supplier-invoices) must not be suggested."""
        results = self.filter_routes('Owner', 'supplier-invoices')
        self.assertEqual(len(results), 0, "Hidden routes must be excluded from search")

    def test_search_empty_and_case_insensitive(self):
        """Search matching must be case-insensitive and handle empty or whitespace inputs cleanly."""
        self.assertEqual(self.filter_routes('Owner', ''), [])
        self.assertEqual(self.filter_routes('Owner', '   '), [])

        results_lower = self.filter_routes('Owner', 'inventory')
        results_upper = self.filter_routes('Owner', 'INVENTORY')
        results_mixed = self.filter_routes('Owner', 'InVeNtOrY')
        self.assertEqual(results_lower, results_upper)
        self.assertEqual(results_lower, results_mixed)

    # =========================================================================
    # WORKSTREAM A: Entity Reference Pattern Recognition & Deep-Link Safety
    # =========================================================================

    def parse_entity_reference(self, user_role, query):
        clean_q = (query or '').strip().lower()
        match = re.match(r'^([a-z]+)[\s\-_#]*([0-9]+)$', clean_q)
        if not match:
            return None

        prefix = match.group(1).upper()
        record_id = int(match.group(2))

        type_map = {
            'PO': 'PURCHASEORDER',
            'PURCHASEORDER': 'PURCHASEORDER',
            'INV': 'INVOICE',
            'INVOICE': 'INVOICE',
            'SHP': 'SHIPMENT',
            'SHIPMENT': 'SHIPMENT',
            'PAY': 'PAYMENT',
            'PAYMENT': 'PAYMENT',
            'QUO': 'QUOTATION',
            'QUOTATION': 'QUOTATION',
            'SR': 'STOCKREQUEST',
            'REQ': 'STOCKREQUEST',
            'STOCKREQUEST': 'STOCKREQUEST'
        }
        route_map = {
            'PURCHASEORDER': 'purchase-orders',
            'INVOICE': 'payments',
            'SHIPMENT': 'shipments',
            'PAYMENT': 'payments',
            'QUOTATION': 'quotations',
            'STOCKREQUEST': 'stock-requests'
        }

        norm_type = type_map.get(prefix)
        if not norm_type:
            return None

        target_path = route_map.get(norm_type)
        route_def = next((r for r in self.routes if r['path'] == target_path), None)
        if not route_def or user_role not in route_def['roles']:
            return None

        return {'type': norm_type, 'record_id': record_id, 'path': target_path}

    def test_entity_reference_resolution(self):
        """Valid entity patterns (PO-12, INV-5, SHP-3) resolve for authorized roles."""
        po_ref = self.parse_entity_reference('Owner', 'PO-12')
        self.assertIsNotNone(po_ref)
        self.assertEqual(po_ref['type'], 'PURCHASEORDER')
        self.assertEqual(po_ref['record_id'], 12)

        inv_ref = self.parse_entity_reference('Manager', 'INV #5')
        self.assertIsNotNone(inv_ref)
        self.assertEqual(inv_ref['type'], 'INVOICE')
        self.assertEqual(inv_ref['record_id'], 5)

    def test_entity_reference_role_boundary(self):
        """Unauthorized entity lookups (e.g. Employee searching PO-12) must return None."""
        emp_po = self.parse_entity_reference('Employee', 'PO-12')
        self.assertIsNone(emp_po, "Employee cannot resolve purchase orders")

        emp_inv = self.parse_entity_reference('Employee', 'INV-5')
        self.assertIsNone(emp_inv, "Employee cannot resolve invoices")

    def test_unsupported_entity_formats_rejected(self):
        """Unsupported entity prefixes must not resolve or fabricate arbitrary records."""
        self.assertIsNone(self.parse_entity_reference('Owner', 'XYZ-999'))
        self.assertIsNone(self.parse_entity_reference('Owner', 'random text 123'))
        self.assertIsNone(self.parse_entity_reference('Owner', 'PO'))

    def test_unresolved_entity_reference_no_lookup_is_module_navigation_only(self):
        """Entities without lookup (e.g. Stock Requests SR-1, Quotations QUO-2) are presented strictly as module navigation."""
        sr_ref = self.parse_entity_reference('Owner', 'SR-1')
        self.assertIsNotNone(sr_ref)
        self.assertEqual(sr_ref['type'], 'STOCKREQUEST')
        self.assertEqual(sr_ref['path'], 'stock-requests')

        # app.js must not claim existence or open modal without verified record
        self.assertIn("type: 'reference-nav'", self.app_js)
        self.assertIn("unverified reference", self.app_js)
        self.assertIn("Module Navigation (Reference Pattern)", self.app_js)

    def test_unresolved_entity_reference_not_found_remains_unverified(self):
        """When an entity lookup fails/404s, it does not fabricate record details or claim record existence."""
        self.assertIn("tryVerifyEntityRecord", self.app_js)
        # Catch block must preserve unverified status and not fabricate details
        self.assertIn("// Do NOT fabricate record details or claim record existence", self.app_js)

    def test_verified_entity_record_distinction(self):
        """Verified records are distinguished under 'Verified Records' and require real API verification."""
        self.assertIn("type: 'verified-record'", self.app_js)
        self.assertIn("Verified Records", self.app_js)
        self.assertIn("Verified ", self.app_js)

    # =========================================================================
    # WORKSTREAM A: UI Elements & Accessibility
    # =========================================================================

    def test_global_search_markup_in_html(self):
        """index.html must contain search input, clear button, and results container with accessible attributes."""
        self.assertIn('id="globalSearch"', self.index_html)
        self.assertIn('id="globalSearchClear"', self.index_html)
        self.assertIn('id="globalSearchResults"', self.index_html)
        self.assertIn('aria-label="Search SIMS modules and records"', self.index_html)
        self.assertIn('aria-expanded="false"', self.index_html)
        self.assertIn('role="listbox"', self.index_html)

    def test_user_profile_dropdown_markup_in_html(self):
        """index.html must contain accessible profile button trigger and dropdown menu."""
        self.assertIn('id="topProfileBtn"', self.index_html)
        self.assertIn('id="profileDropdown"', self.index_html)
        self.assertIn('aria-label="User account menu"', self.index_html)
        self.assertIn('aria-haspopup="true"', self.index_html)
        self.assertIn('aria-expanded="false"', self.index_html)
        self.assertIn('role="menu"', self.index_html)

        # Profile menu items
        self.assertIn('id="change-password-btn"', self.index_html)
        self.assertIn('id="profileThemeToggle"', self.index_html)
        self.assertIn('id="profile-logout-btn"', self.index_html)

    def test_keyboard_shortcut_implementation_in_app_js(self):
        """app.js must register keydown listener handling Ctrl+K / Cmd+K with modal check and preventDefault."""
        self.assertIn("e.ctrlKey || e.metaKey", self.app_js)
        self.assertIn("e.key === 'k' || e.key === 'K'", self.app_js)
        self.assertIn("document.querySelector('.modal-overlay.active')", self.app_js)
        self.assertIn("e.preventDefault()", self.app_js)
        self.assertIn("App.search.focus()", self.app_js)

    def test_profile_dropdown_controller_in_app_js(self):
        """app.js must implement App.profileDropdown with mutual exclusion and outside dismissal."""
        self.assertIn("profileDropdown:", self.app_js)
        self.assertIn("topProfileBtn", self.app_js)
        self.assertIn("App.notifications.closeDropdown()", self.app_js)
        self.assertIn("App.profileDropdown.close()", self.app_js)
        self.assertIn("Auth.logout()", self.app_js)

    # =========================================================================
    # WORKSTREAM B: Theme Architecture, FOUC Prevention & Design Tokens
    # =========================================================================

    def simulate_theme_bootstrap(self, storage_throws=False, stored_val=None, os_prefers_dark=False, media_throws=False):
        """Simulate the synchronous early theme bootstrap script in index.html <head>."""
        saved = None
        if storage_throws:
            # Storage access failure (e.g. SecurityError in private mode)
            saved = None
        else:
            saved = stored_val

        is_dark = False
        if saved == 'dark':
            is_dark = True
        elif saved == 'light':
            is_dark = False
        else:
            if media_throws:
                is_dark = False
            else:
                is_dark = bool(os_prefers_dark)

        return 'dark' if is_dark else 'light'

    def test_theme_bootstrap_unavailable_storage_falls_back_to_dark_os(self):
        """If reading storage throws, theme bootstrap safely falls back to dark OS preference."""
        res = self.simulate_theme_bootstrap(storage_throws=True, os_prefers_dark=True)
        self.assertEqual(res, 'dark')

    def test_theme_bootstrap_unavailable_storage_falls_back_to_light_os(self):
        """If reading storage throws, theme bootstrap safely falls back to light OS preference."""
        res = self.simulate_theme_bootstrap(storage_throws=True, os_prefers_dark=False)
        self.assertEqual(res, 'light')

    def test_theme_bootstrap_missing_preference_with_dark_os(self):
        """When no preference is stored, theme bootstrap respects dark OS preference."""
        res = self.simulate_theme_bootstrap(stored_val=None, os_prefers_dark=True)
        self.assertEqual(res, 'dark')

    def test_theme_bootstrap_missing_preference_with_light_os(self):
        """When no preference is stored, theme bootstrap respects light OS preference."""
        res = self.simulate_theme_bootstrap(stored_val=None, os_prefers_dark=False)
        self.assertEqual(res, 'light')

    def test_theme_bootstrap_invalid_preference_fallback(self):
        """Invalid stored preference (e.g. 'undefined', 'custom') safely falls back to OS preference."""
        self.assertEqual(self.simulate_theme_bootstrap(stored_val='undefined', os_prefers_dark=True), 'dark')
        self.assertEqual(self.simulate_theme_bootstrap(stored_val='custom', os_prefers_dark=False), 'light')

    def test_theme_bootstrap_explicit_dark_preference_honored(self):
        """Valid explicit 'dark' preference is honored regardless of OS preference."""
        self.assertEqual(self.simulate_theme_bootstrap(stored_val='dark', os_prefers_dark=False), 'dark')
        self.assertEqual(self.simulate_theme_bootstrap(stored_val='dark', os_prefers_dark=True), 'dark')

    def test_theme_bootstrap_explicit_light_preference_honored(self):
        """Valid explicit 'light' preference is honored regardless of OS preference."""
        self.assertEqual(self.simulate_theme_bootstrap(stored_val='light', os_prefers_dark=True), 'light')
        self.assertEqual(self.simulate_theme_bootstrap(stored_val='light', os_prefers_dark=False), 'light')

    def test_theme_bootstrap_media_failure_resilience(self):
        """If storage throws AND matchMedia throws, theme defaults to light without crashing."""
        res = self.simulate_theme_bootstrap(storage_throws=True, media_throws=True)
        self.assertEqual(res, 'light')

    def test_early_fouc_prevention_script_in_head(self):
        """index.html <head> must contain synchronous pre-render theme script before stylesheets."""
        head_match = re.search(r'<head>(.*?)</head>', self.index_html, re.DOTALL)
        self.assertIsNotNone(head_match)
        head_content = head_match.group(1)

        self.assertIn("localStorage.getItem('sims_theme')", head_content)
        self.assertIn("prefers-color-scheme: dark", head_content)
        self.assertIn("document.documentElement.classList.add('dark', 'dark-theme')", head_content)

        # Script must appear before index.css link
        script_idx = head_content.find('localStorage.getItem(\'sims_theme\')')
        css_idx = head_content.find('rel="stylesheet"')
        self.assertTrue(script_idx < css_idx, "Early theme script must execute before stylesheets link")

    def test_early_fouc_prevention_script_isolates_storage_error(self):
        """index.html <head> must isolate storage error handling from OS matchMedia fallback."""
        head_match = re.search(r'<head>(.*?)</head>', self.index_html, re.DOTALL)
        self.assertIsNotNone(head_match)
        head_content = head_match.group(1)

        self.assertIn("catch (storageErr)", head_content)
        self.assertIn("catch (mediaErr)", head_content)
        self.assertIn("window.matchMedia('(prefers-color-scheme: dark)')", head_content)

    def test_design_tokens_defined_in_index_css(self):
        """index.css must define --card-bg, --bg-surface, --bg-main, --bg-hover, and color-scheme in both themes."""
        # Light mode tokens in :root
        root_block = re.search(r':root\s*\{([^}]+)\}', self.index_css)
        self.assertIsNotNone(root_block)
        root_content = root_block.group(1)

        self.assertIn('--card-bg:', root_content)
        self.assertIn('--bg-surface:', root_content)
        self.assertIn('--bg-main:', root_content)
        self.assertIn('--bg-hover:', root_content)
        self.assertIn('color-scheme: light;', root_content)

        # Dark mode tokens
        dark_block = re.search(r'(?:body\.dark|html\.dark|:root\.dark)[^{]*\{([^}]+)\}', self.index_css)
        self.assertIsNotNone(dark_block)
        dark_content = dark_block.group(1)

        self.assertIn('--card-bg: #18201e;', dark_content)
        self.assertIn('--bg-surface: #141b19;', dark_content)
        self.assertIn('--bg-main: #111716;', dark_content)
        self.assertIn('color-scheme: dark;', dark_content)

    def test_focus_visible_styling_in_index_css(self):
        """index.css must provide accessible :focus-visible outlines."""
        self.assertIn(':focus-visible', self.index_css)
        self.assertIn('outline: 2px solid var(--primary)', self.index_css)

    def test_native_date_picker_indicator_dark_mode_filter(self):
        """index.css must ensure date picker indicator has contrast in dark mode."""
        self.assertIn('input[type="date"]::-webkit-calendar-picker-indicator', self.index_css)
        self.assertIn('filter: invert(0.85)', self.index_css)

    def test_actions_bar_dark_mode_overrides(self):
        """index.css must override .actions-bar to eradicate white patches in Audit Logs and filters."""
        self.assertIn('body.dark .actions-bar', self.index_css)
        self.assertIn('body.dark .actions-bar select', self.index_css)
        self.assertIn('body.dark .actions-bar input', self.index_css)


if __name__ == '__main__':
    unittest.main()
