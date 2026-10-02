import unittest
import os
import sys
from unittest.mock import patch

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.extensions import get_db_connection
from app.services.team3.status_service import LATENCY_WARNING_THRESHOLD_MS


class Team3SystemStatusAndHealthTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Login and obtain tokens for each role
        cls.owner_token = cls._get_token("demo_owner", "password123")
        cls.manager_token = cls._get_token("demo_manager", "password123")
        cls.employee_token = cls._get_token("demo_employee", "password123")
        cls.supplier_token = cls._get_token("demo_supplier", "password123")

    @classmethod
    def _get_token(cls, username, password):
        resp = cls.client.post("/api/auth/login", json={
            "username": username,
            "password": password
        })
        data = resp.get_json() or {}
        return data.get("access_token")

    def test_01_public_liveness_endpoint(self):
        """Test GET /api/status/ returns minimal public liveness ping without credentials"""
        resp = self.client.get("/api/status/")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "UP")
        self.assertNotIn("database", data)
        self.assertNotIn("modules", data)

        resp_no_slash = self.client.get("/api/status")
        self.assertEqual(resp_no_slash.status_code, 200)
        self.assertEqual(resp_no_slash.get_json().get("status"), "UP")

    def test_02_detailed_health_owner_access(self):
        """Test Owner role can access detailed health endpoint and receives valid telemetry"""
        resp = self.client.get(
            "/api/status/health",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        # Required contract keys
        self.assertIn("overall_status", data)
        self.assertIn("backend", data)
        self.assertIn("database", data)
        self.assertIn("modules", data)
        self.assertIn("uptime_seconds", data)
        self.assertIn("checked_at", data)
        self.assertIn("performance_warning", data)

        # Database contract keys (connectivity separated from performance)
        db = data["database"]
        self.assertIn("status", db)
        self.assertIn("latency_ms", db)
        self.assertIn("performance", db)
        self.assertIn("performance_warning", db)
        self.assertIn("latency_threshold_ms", db)
        self.assertEqual(db["latency_threshold_ms"], LATENCY_WARNING_THRESHOLD_MS)

    def test_03_detailed_health_manager_access(self):
        """Test Manager role can access detailed health endpoint"""
        resp = self.client.get(
            "/api/status/health",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn(data["overall_status"], ["HEALTHY", "DEGRADED"])
        self.assertEqual(data["backend"]["status"], "UP")
        self.assertEqual(data["database"]["status"], "CONNECTED")

    def test_04_detailed_health_access_denied_for_unauthorized_roles(self):
        """Test Employee and Supplier roles are rejected with 403 Forbidden"""
        resp_emp = self.client.get(
            "/api/status/health",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp_emp.status_code, 403)
        self.assertEqual(resp_emp.get_json().get("error"), "Access denied")

        resp_sup = self.client.get(
            "/api/status/health",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp_sup.status_code, 403)
        self.assertEqual(resp_sup.get_json().get("error"), "Access denied")

    def test_05_detailed_health_access_denied_for_anonymous_requests(self):
        """Test unauthenticated requests are rejected with 401 Unauthorized"""
        resp_no_token = self.client.get("/api/status/health")
        self.assertEqual(resp_no_token.status_code, 401)

        resp_bad_token = self.client.get(
            "/api/status/health",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        self.assertIn(resp_bad_token.status_code, [401, 422])

    def test_06_normal_latency_health_policy(self):
        """Test normal latency (<= 500ms) produces HEALTHY overall status without performance warning"""
        # Simulate normal latency of 125.0 ms
        with patch("time.perf_counter", side_effect=[0.0, 0.125]):
            resp = self.client.get(
                "/api/status/health",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            db = data["database"]

            self.assertEqual(db["status"], "CONNECTED")
            self.assertEqual(db["performance"], "NORMAL")
            self.assertFalse(db["performance_warning"])
            self.assertFalse(data["performance_warning"])
            self.assertEqual(data["overall_status"], "HEALTHY")
            self.assertAlmostEqual(db["latency_ms"], 125.0, places=1)

    def test_07_elevated_latency_performance_warning(self):
        """Test elevated latency (> 500ms) produces performance warning and DEGRADED overall status while DB remains CONNECTED"""
        # Simulate elevated latency of 650.0 ms (0.650 seconds)
        with patch("time.perf_counter", side_effect=[0.0, 0.650]):
            resp = self.client.get(
                "/api/status/health",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            db = data["database"]

            # Database connectivity remains CONNECTED (separate from performance!)
            self.assertEqual(db["status"], "CONNECTED")
            # Performance status is ELEVATED
            self.assertEqual(db["performance"], "ELEVATED")
            # Performance warning is flagged
            self.assertTrue(db["performance_warning"])
            self.assertTrue(data["performance_warning"])
            # Overall health calculation policy flags DEGRADED due to elevated response latency
            self.assertEqual(data["overall_status"], "DEGRADED")
            self.assertAlmostEqual(db["latency_ms"], 650.0, places=1)

    def test_08_database_failure_returns_503_degraded(self):
        """Test database failure returns 503, reports DISCONNECTED, UNAVAILABLE, and DEGRADED"""
        with patch("app.services.team3.status_service.get_db_connection") as mock_conn:
            mock_conn.side_effect = Exception("Connection pool exhausted or PostgreSQL offline")

            resp = self.client.get(
                "/api/status/health",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp.status_code, 503)
            data = resp.get_json()
            db = data["database"]

            self.assertEqual(data["overall_status"], "DEGRADED")
            self.assertEqual(data["backend"]["status"], "UP")
            self.assertEqual(db["status"], "DISCONNECTED")
            self.assertEqual(db["performance"], "UNAVAILABLE")
            self.assertFalse(db["performance_warning"])
            self.assertIsNone(db["latency_ms"])
            self.assertEqual(data["modules"], [])

    def test_09_inventory_not_ready_reports_degraded(self):
        """Test when Inventory module is not READY, overall status is DEGRADED, not falsely READY"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE "SystemStatus"
                SET status = 'SYNCING', message = 'Synchronizing warehouse stock'
                WHERE module_name = 'Inventory'
            ''')
            conn.commit()

            resp = self.client.get(
                "/api/status/health",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data["overall_status"], "DEGRADED")

            inventory_mod = next((m for m in data["modules"] if m["name"] == "Inventory"), None)
            self.assertIsNotNone(inventory_mod)
            self.assertEqual(inventory_mod["status"], "SYNCING")

        finally:
            # Restore to READY
            cursor.execute('''
                UPDATE "SystemStatus"
                SET status = 'READY', progress = 100, message = 'Inventory is ready'
                WHERE module_name = 'Inventory'
            ''')
            conn.commit()
            cursor.close()
            conn.close()

        # Confirm restored health
        resp_restored = self.client.get(
            "/api/status/health",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_restored.status_code, 200)

    def test_10_existing_reports_status_endpoint_compatibility(self):
        """Test existing GET /api/reports/status remains functional with original payload"""
        resp = self.client.get("/api/reports/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "READY")
        self.assertEqual(data.get("progress"), 100)
        self.assertIn("message", data)
        self.assertIn("updated_at", data)


if __name__ == "__main__":
    unittest.main()
