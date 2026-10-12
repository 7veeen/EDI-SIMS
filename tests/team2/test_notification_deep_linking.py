import os
import subprocess
import unittest
from pathlib import Path


class NotificationDeepLinkingPhase2TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]

    def test_01_app_js_normalization_and_dispatcher_helpers_exist(self):
        """Verify frontend/js/app.js contains normalizeReferenceType and enhanced navigateToReference."""
        app_js_path = self.repo_root / "frontend" / "js" / "app.js"
        self.assertTrue(app_js_path.exists(), "frontend/js/app.js must exist")
        content = app_js_path.read_text(encoding="utf-8")

        self.assertIn("normalizeReferenceType(type)", content)
        self.assertIn("navigateToReference(referenceType, referenceId", content)
        self.assertIn("'SHIPMENT'", content)
        self.assertIn("'PURCHASEORDER'", content)
        self.assertIn("'PRODUCT'", content)
        self.assertIn("'QUOTATION'", content)
        self.assertIn("'STOCKREQUEST'", content)
        self.assertIn("'STOCKTRANSACTION'", content)

    def test_02_target_page_modal_functions_exist(self):
        """Verify each target page implements the modal or filter method referenced in the dispatcher."""
        # 1. shipments.js -> openShipmentDetailsModal
        shipments_js = (self.repo_root / "frontend" / "js" / "pages" / "shipments.js").read_text(encoding="utf-8")
        self.assertIn("openShipmentDetailsModal", shipments_js)

        # 2. purchase-orders.js -> viewPODetails
        po_js = (self.repo_root / "frontend" / "js" / "pages" / "purchase-orders.js").read_text(encoding="utf-8")
        self.assertIn("viewPODetails", po_js)

        # 3. products.js -> showProductModal
        products_js = (self.repo_root / "frontend" / "js" / "pages" / "products.js").read_text(encoding="utf-8")
        self.assertIn("showProductModal", products_js)

        # 4. quotations.js -> openQuotationDetailsModal
        quotes_js = (self.repo_root / "frontend" / "js" / "pages" / "quotations.js").read_text(encoding="utf-8")
        self.assertIn("openQuotationDetailsModal", quotes_js)

        # 5. stock-requests.js -> openDetailsModal
        sr_js = (self.repo_root / "frontend" / "js" / "pages" / "stock-requests.js").read_text(encoding="utf-8")
        self.assertIn("openDetailsModal", sr_js)

        # 6. stock-transactions.js -> applyFilters
        st_js = (self.repo_root / "frontend" / "js" / "pages" / "stock-transactions.js").read_text(encoding="utf-8")
        self.assertIn("applyFilters", st_js)

    def test_03_route_rbac_definitions_aligned(self):
        """Verify App.routes matches expected RBAC permissions for deep-linking destinations."""
        app_js_path = self.repo_root / "frontend" / "js" / "app.js"
        content = app_js_path.read_text(encoding="utf-8")

        # Purchase Orders: Owner, Manager, Supplier (Employee excluded)
        self.assertIn("path: 'purchase-orders'", content)
        # Quotations: Owner, Manager, Supplier (Employee excluded)
        self.assertIn("path: 'quotations'", content)
        # Stock Requests: Owner, Manager, Supplier (Employee excluded)
        self.assertIn("path: 'stock-requests'", content)
        # Products: Owner, Manager, Employee (Supplier excluded)
        self.assertIn("path: 'products'", content)
        # Shipments: Owner, Manager, Supplier, Employee
        self.assertIn("path: 'shipments'", content)
        # Stock Transactions: Owner, Manager, Employee (Supplier excluded)
        self.assertIn("path: 'stock-transactions'", content)

    def test_04_node_deep_linking_suite_passes(self):
        """Execute the focused Node.js test suite and assert a 0 return code."""
        node_script = self.repo_root / "tests" / "team2" / "test_notification_deep_linking.js"
        self.assertTrue(node_script.exists(), "test_notification_deep_linking.js must exist")

        result = subprocess.run(
            ["node", str(node_script)],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True
        )

        self.assertEqual(
            result.returncode,
            0,
            f"Node deep-linking verification failed with output:\n{result.stdout}\n{result.stderr}"
        )
        self.assertIn("ALL 4 TEST SUITES PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
