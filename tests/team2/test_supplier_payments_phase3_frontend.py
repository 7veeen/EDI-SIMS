import os
import subprocess
import unittest
from pathlib import Path


class SupplierPaymentsPhase3FrontendTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]

    def test_01_phase3_deliverable_files_exist_and_non_empty(self):
        """Verify all Phase 3 frontend files exist, are properly placed, and non-empty."""
        expected_files = [
            self.repo_root / "frontend" / "css" / "supplier-invoices.css",
            self.repo_root / "frontend" / "pages" / "supplier-invoices.html",
            self.repo_root / "frontend" / "js" / "pages" / "payments.js",
            self.repo_root / "frontend" / "js" / "pages" / "supplier-invoices.js",
            self.repo_root / "frontend" / "js" / "api" / "api.js",
            self.repo_root / "frontend" / "js" / "app.js",
            self.repo_root / "frontend" / "index.html",
        ]
        for f in expected_files:
            self.assertTrue(f.exists(), f"File must exist: {f}")
            self.assertGreater(f.stat().st_size, 50, f"File must not be empty or stub: {f}")

    def test_02_index_html_integration(self):
        """Verify index.html includes the stylesheet and script tags for invoices & payments."""
        index_html_path = self.repo_root / "frontend" / "index.html"
        content = index_html_path.read_text(encoding="utf-8")

        self.assertIn("css/supplier-invoices.css", content)
        self.assertIn("js/pages/payments.js", content)
        self.assertIn("js/pages/supplier-invoices.js", content)

    def test_03_api_js_invoice_and_payment_methods(self):
        """Verify api.js exposes all necessary invoice and payment endpoints."""
        api_js_path = self.repo_root / "frontend" / "js" / "api" / "api.js"
        content = api_js_path.read_text(encoding="utf-8")

        required_methods = [
            "getInvoices",
            "getInvoice",
            "submitInvoice",
            "approveInvoice",
            "rejectInvoice",
            "cancelInvoice",
            "getInvoicePayments",
            "getPayments",
            "getPayment",
            "recordPayment",
        ]
        for method in required_methods:
            self.assertIn(method, content, f"api.js must implement method {method}")

    def test_04_app_js_rbac_route_permissions(self):
        """Verify app.js routing table grants financial access to Owner, Manager, Supplier and blocks Employee."""
        app_js_path = self.repo_root / "frontend" / "js" / "app.js"
        content = app_js_path.read_text(encoding="utf-8")

        payments_lines = [line for line in content.splitlines() if "path: 'payments'" in line]
        self.assertTrue(len(payments_lines) > 0, "app.js must define payments route")
        payments_line = payments_lines[0]

        self.assertIn("roles: ['Owner', 'Manager', 'Supplier']", payments_line)
        self.assertNotIn("Employee", payments_line, "Employee must NOT be present in payments roles")
        
        # Verify hidden route logic exists
        self.assertIn("!route.hidden", content)

    def test_05_node_frontend_logic_runner(self):
        """Run Node.js DOM and UI logic test runner to verify badges, formatters, and UI guards."""
        test_script = self.repo_root / "tests" / "team2" / "test_frontend_logic.js"
        result = subprocess.run(
            ["node", str(test_script)],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, f"Node tests failed: {result.stderr or result.stdout}")
        self.assertIn("ALL 10 FRONTEND INTEGRATION CHECKS PASSED SUCCESSFULLY!", result.stdout)


if __name__ == "__main__":
    unittest.main()
