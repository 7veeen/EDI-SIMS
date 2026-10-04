import unittest
import requests
import json

BASE_URL = "http://127.0.0.1:5000/api"

class TestSupplierDashboardEnhancements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Login as demo_supplier
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "demo_supplier",
            "password": "password123"
        })
        assert resp.status_code == 200, f"demo_supplier login failed: {resp.text}"
        cls.demo_token = resp.json().get("access_token")
        cls.demo_headers = {"Authorization": f"Bearer {cls.demo_token}"}

        # 2. Login as supplier1
        resp2 = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "supplier1",
            "password": "password123"
        })
        assert resp2.status_code == 200, f"supplier1 login failed: {resp2.text}"
        cls.s1_token = resp2.json().get("access_token")
        cls.s1_headers = {"Authorization": f"Bearer {cls.s1_token}"}

        # 3. Login as manager
        resp3 = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "demo_manager",
            "password": "password123"
        })
        assert resp3.status_code == 200, f"manager login failed: {resp3.text}"
        cls.mgr_token = resp3.json().get("access_token")
        cls.mgr_headers = {"Authorization": f"Bearer {cls.mgr_token}"}

    def test_01_demo_supplier_dashboard_payload_structure(self):
        """Verify GET /api/dashboard/supplier returns all required enhanced fields for demo_supplier."""
        res = requests.get(f"{BASE_URL}/dashboard/supplier", headers=self.demo_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Check identity
        self.assertEqual(data.get("supplier_id"), 5)
        self.assertEqual(data.get("supplier_name"), "Demo Supplier Company")

        # Check 4 Primary KPI numbers
        self.assertIn("open_requests", data)
        self.assertIn("pending_quotations", data)
        self.assertIn("active_pos", data)
        self.assertIn("pending_deliveries", data)
        self.assertIsInstance(data["open_requests"], int)
        self.assertIsInstance(data["pending_quotations"], int)
        self.assertIsInstance(data["active_pos"], int)
        self.assertIsInstance(data["pending_deliveries"], int)

        # Check Pending Payments (MUST NOT be fabricated; None/null)
        self.assertIn("pending_payments", data)
        self.assertIsNone(data["pending_payments"])
        self.assertFalse(data.get("has_payment_module", True))

        # Check Shipment Status dictionary
        self.assertIn("shipment_stats", data)
        stats = data["shipment_stats"]
        for key in ["ready_for_shipment", "dispatched", "in_transit", "delayed", "delivered", "total"]:
            self.assertIn(key, stats)
            self.assertIsInstance(stats[key], int)

        # Check Needs Your Attention items
        self.assertIn("attention_items", data)
        self.assertIsInstance(data["attention_items"], list)
        for item in data["attention_items"]:
            self.assertIn("type", item)
            self.assertIn("title", item)
            self.assertIn("status", item)
            self.assertIn("target_page", item)
            self.assertIn("action_label", item)

        # Check Performance metrics
        self.assertIn("on_time_delivery_rate", data)
        self.assertIn("quotation_acceptance_rate", data)
        self.assertIn("order_acceptance_rate", data)
        self.assertIn("profile_completion", data)

        # Check Recent POs and Stock Requests
        self.assertIn("recent_orders", data)
        self.assertIn("recent_stock_requests", data)
        self.assertIn("recent_activity", data)

    def test_02_supplier1_dashboard_payload_structure(self):
        """Verify GET /api/dashboard/supplier returns correct structure for supplier1."""
        res = requests.get(f"{BASE_URL}/dashboard/supplier", headers=self.s1_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data.get("supplier_id"), 4)
        self.assertEqual(data.get("supplier_name"), "Supplier 1 Company")
        self.assertIsNone(data.get("pending_payments"))
        self.assertIn("pending_deliveries", data)
        self.assertIn("shipment_stats", data)
        self.assertIn("attention_items", data)

    def test_03_supplier_isolation_on_dashboard(self):
        """Verify Supplier 1 and Demo Supplier see mutually exclusive data."""
        res_demo = requests.get(f"{BASE_URL}/dashboard/supplier", headers=self.demo_headers).json()
        res_s1 = requests.get(f"{BASE_URL}/dashboard/supplier", headers=self.s1_headers).json()

        demo_po_ids = {o["purchase_order_id"] for o in res_demo.get("recent_orders", [])}
        s1_po_ids = {o["purchase_order_id"] for o in res_s1.get("recent_orders", [])}
        # Sets must not overlap if orders belong to specific suppliers
        overlap = demo_po_ids.intersection(s1_po_ids)
        self.assertEqual(len(overlap), 0, f"Cross-tenant PO overlap found: {overlap}")

        demo_sr_ids = {sr["stock_request_id"] for sr in res_demo.get("recent_stock_requests", [])}
        s1_sr_ids = {sr["stock_request_id"] for sr in res_s1.get("recent_stock_requests", [])}
        overlap_sr = demo_sr_ids.intersection(s1_sr_ids)
        self.assertEqual(len(overlap_sr), 0, f"Cross-tenant SR overlap found: {overlap_sr}")

    def test_04_cross_tenant_stock_request_access_denied(self):
        """Ensure supplier1 cannot access demo_supplier's stock requests."""
        # Find a stock request belonging to demo_supplier (supplier_id = 5)
        res = requests.get(f"{BASE_URL}/stock-requests/", headers=self.demo_headers)
        self.assertEqual(res.status_code, 200)
        demo_requests = res.json().get("stock_requests", [])
        if demo_requests:
            demo_sr_id = demo_requests[0]["stock_request_id"]
            # Attempt to access using supplier1 token
            cross_res = requests.get(f"{BASE_URL}/stock-requests/{demo_sr_id}", headers=self.s1_headers)
            self.assertIn(cross_res.status_code, [403, 404], f"Expected 403/404 for cross-tenant access, got {cross_res.status_code}")

    def test_05_shipment_counts_match_shipments_api(self):
        """Verify shipment count in dashboard matches GET /api/shipments/ count."""
        dash_res = requests.get(f"{BASE_URL}/dashboard/supplier", headers=self.demo_headers).json()
        ship_res = requests.get(f"{BASE_URL}/shipments/", headers=self.demo_headers).json()

        dash_total = dash_res["shipment_stats"]["total"]
        actual_total = len(ship_res) if isinstance(ship_res, list) else len(ship_res.get("shipments", []))
        self.assertEqual(dash_total, actual_total)

    def test_06_attention_items_are_genuine(self):
        """Verify all items in attention_items represent real actionable states."""
        dash_res = requests.get(f"{BASE_URL}/dashboard/supplier", headers=self.demo_headers).json()
        attention_items = dash_res.get("attention_items", [])
        for item in attention_items:
            # Must be one of the recognized actionable types
            self.assertIn(item["type"], ["stock_request", "purchase_order", "delayed_shipment"])
            self.assertTrue(item["title"])
            self.assertTrue(item["action_label"])
            self.assertIn(item["target_page"], ["stock-requests", "purchase-orders", "shipments"])

    def test_07_regression_step1_products_inventory(self):
        """Regression test for Step 1: Products and Inventory."""
        p_res = requests.get(f"{BASE_URL}/products", headers=self.mgr_headers)
        self.assertEqual(p_res.status_code, 200)
        i_res = requests.get(f"{BASE_URL}/inventory", headers=self.mgr_headers)
        self.assertEqual(i_res.status_code, 200)

    def test_08_regression_step3_purchase_orders(self):
        """Regression test for Step 3: Purchase Orders."""
        po_res = requests.get(f"{BASE_URL}/purchase-orders", headers=self.mgr_headers)
        self.assertEqual(po_res.status_code, 200)

    def test_09_regression_step4_quotations(self):
        """Regression test for Step 4: Quotations."""
        q_res = requests.get(f"{BASE_URL}/quotations", headers=self.mgr_headers)
        self.assertEqual(q_res.status_code, 200)

    def test_10_regression_step5_shipments(self):
        """Regression test for Step 5: Shipments."""
        s_res = requests.get(f"{BASE_URL}/shipments", headers=self.mgr_headers)
        self.assertEqual(s_res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
