"""
Test Suite: Supplier Portal Corrections & Stock Requests Module
Verifies:
1. Supplier Dashboard Live DB Data & Zero Mock Metrics
2. JWT-Based Supplier Resolution & Strict Supplier Isolation
3. Stock Requests Creation (Manager/Owner)
4. Stock Requests Retrieval & Multi-Item Support
5. Supplier Response (Accept/Reject) & Linked Quotation Generation
6. Employee Access Denial (RBAC)
7. Full Regression Testing (Steps 1–6)
"""

import os
import sys
import unittest
import json
from datetime import datetime, timedelta

# Ensure backend directory is in python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import create_app
from app.extensions import get_db_connection


class TestSupplierPortalAndStockRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Login Helper
        cls.tokens = {}
        for username in ['demo_owner', 'demo_manager', 'demo_employee', 'demo_supplier', 'supplier1']:
            res = cls.client.post('/api/auth/login', json={
                'username': username,
                'password': 'password123'
            })
            if res.status_code == 200:
                cls.tokens[username] = res.get_json()['access_token']
            else:
                print(f"Warning: Login failed for {username}: {res.get_json()}")

    def get_headers(self, username):
        return {
            'Authorization': f"Bearer {self.tokens[username]}",
            'Content-Type': 'application/json'
        }

    # =========================================================================
    # PART A: SUPPLIER DASHBOARD TESTS
    # =========================================================================
    def test_01_supplier_dashboard_authenticated(self):
        """Test authenticated supplier receives database-driven dashboard metrics."""
        headers = self.get_headers('demo_supplier')
        res = self.client.get('/api/dashboard/supplier', headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Verify all expected keys are present
        expected_keys = [
            'open_requests', 'pending_quotations', 'active_pos', 'pending_payments',
            'has_payment_module', 'on_time_delivery_rate', 'quotation_acceptance_rate',
            'order_acceptance_rate', 'profile_completion', 'recent_stock_requests',
            'recent_orders', 'supplier'
        ]
        for key in expected_keys:
            self.assertIn(key, data, f"Key {key} missing from supplier dashboard")

        # Verify no hardcoded strings
        self.assertNotEqual(data.get('pending_payments'), 284000)
        self.assertIsNone(data.get('pending_payments'))  # Safely None since no payments table
        self.assertFalse(data.get('has_payment_module'))
        self.assertEqual(data['supplier']['supplier_id'], 5)

    def test_02_supplier_dashboard_isolation(self):
        """Test supplier 1 and supplier 2 see isolated metrics."""
        headers1 = self.get_headers('supplier1')
        res1 = self.client.get('/api/dashboard/supplier', headers=headers1)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertEqual(data1['supplier']['supplier_id'], 4)

        headers2 = self.get_headers('demo_supplier')
        res2 = self.client.get('/api/dashboard/supplier', headers=headers2)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2['supplier']['supplier_id'], 5)

        # Confirm isolation: supplier1 has 0 open requests (unless assigned)
        self.assertEqual(data1['supplier']['supplier_name'], 'Supplier 1 Company')
        self.assertEqual(data2['supplier']['supplier_name'], 'Demo Supplier Company')

    # =========================================================================
    # PART B & C: STOCK REQUESTS BACKEND & RBAC
    # =========================================================================
    def test_03_manager_creates_stock_request(self):
        """Test Manager can create a stock request with multiple product items."""
        headers = self.get_headers('demo_manager')
        payload = {
            'supplier_id': 4,  # Assign to supplier1
            'priority': 'Urgent',
            'required_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'notes': 'Urgent restock needed for warehouse branch A',
            'items': [
                {'product_id': 1, 'requested_quantity': 30, 'notes': 'Item 1 batch'},
                {'product_id': 2, 'requested_quantity': 15, 'notes': 'Item 2 batch'}
            ]
        }
        res = self.client.post('/api/stock-requests/', headers=headers, json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn('stock_request', data)
        sr = data['stock_request']
        self.assertTrue(sr['request_number'].startswith('SR-'))
        self.assertEqual(sr['supplier_id'], 4)
        self.assertEqual(sr['status'], 'Pending')
        self.assertEqual(sr['priority'], 'Urgent')
        self.assertEqual(sr['items_count'], 2)

        # Store for subsequent tests
        self.__class__.created_sr_id = sr['stock_request_id']

    def test_04_supplier_isolation_on_stock_requests_list(self):
        """Test supplier only sees stock requests assigned to them."""
        # Supplier 1 (supplier_id = 4) SHOULD see the newly created request
        headers1 = self.get_headers('supplier1')
        res1 = self.client.get('/api/stock-requests/', headers=headers1)
        self.assertEqual(res1.status_code, 200)
        list1 = res1.get_json()['stock_requests']
        req_ids1 = [r['stock_request_id'] for r in list1]
        self.assertIn(self.__class__.created_sr_id, req_ids1)

        # Supplier 2 (demo_supplier, supplier_id = 5) must NOT see this request
        headers2 = self.get_headers('demo_supplier')
        res2 = self.client.get('/api/stock-requests/', headers=headers2)
        self.assertEqual(res2.status_code, 200)
        list2 = res2.get_json()['stock_requests']
        req_ids2 = [r['stock_request_id'] for r in list2]
        self.assertNotIn(self.__class__.created_sr_id, req_ids2)

    def test_05_supplier_isolation_on_stock_request_details(self):
        """Test unassigned supplier is denied 403 when requesting details by ID."""
        sr_id = self.__class__.created_sr_id

        # Supplier 2 (unassigned) tries to view it
        headers2 = self.get_headers('demo_supplier')
        res2 = self.client.get(f'/api/stock-requests/{sr_id}', headers=headers2)
        self.assertEqual(res2.status_code, 403)
        self.assertIn('Access denied', res2.get_json()['error'])

        # Supplier 1 (assigned) views it successfully
        headers1 = self.get_headers('supplier1')
        res1 = self.client.get(f'/api/stock-requests/{sr_id}', headers=headers1)
        self.assertEqual(res1.status_code, 200)
        sr = res1.get_json()['stock_request']
        self.assertEqual(sr['stock_request_id'], sr_id)
        self.assertEqual(len(sr['items']), 2)
        self.assertEqual(sr['total_quantity'], 45)

    def test_06_employee_access_denied_to_stock_requests(self):
        """Test Employee role is blocked from viewing stock requests."""
        headers = self.get_headers('demo_employee')
        res = self.client.get('/api/stock-requests/', headers=headers)
        self.assertEqual(res.status_code, 403)

    def test_07_unassigned_supplier_cannot_respond(self):
        """Test supplier cannot respond to a stock request not belonging to them."""
        sr_id = self.__class__.created_sr_id
        headers2 = self.get_headers('demo_supplier')
        res2 = self.client.patch(f'/api/stock-requests/{sr_id}/respond', headers=headers2, json={
            'action': 'Accept',
            'notes': 'Sneaky accept attempt'
        })
        self.assertEqual(res2.status_code, 403)
        self.assertIn('Access denied', res2.get_json()['error'])

    def test_08_assigned_supplier_responds_and_creates_quotation(self):
        """Test assigned supplier accepts stock request with quoted price, automatically generating a quotation."""
        sr_id = self.__class__.created_sr_id
        headers1 = self.get_headers('supplier1')
        res = self.client.patch(f'/api/stock-requests/{sr_id}/respond', headers=headers1, json={
            'action': 'Accept',
            'notes': 'Stock is available in our regional distribution warehouse.',
            'quoted_price': 180.0,
            'valid_until': (datetime.now() + timedelta(days=20)).strftime('%Y-%m-%d')
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'Quoted')
        self.assertIsNotNone(data['quotation_id'])

        # Verify linked quotation was created in SupplierQuotations
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT quotation_id, quotation_number, status, quoted_price, stock_request_id FROM "SupplierQuotations" WHERE quotation_id = %s', (data['quotation_id'],))
        q = cur.fetchone()
        self.assertIsNotNone(q)
        self.assertEqual(q[2], 'Pending')
        self.assertEqual(float(q[3]), 180.0)
        self.assertEqual(q[4], sr_id)
        cur.close()
        conn.close()

    def test_09_supplier_reject_stock_request(self):
        """Test supplier can reject a stock request."""
        # Create a request for demo_supplier
        m_headers = self.get_headers('demo_manager')
        c_res = self.client.post('/api/stock-requests/', headers=m_headers, json={
            'supplier_id': 5,
            'priority': 'Low',
            'notes': 'Non-urgent test request',
            'items': [{'product_id': 1, 'requested_quantity': 5}]
        })
        self.assertEqual(c_res.status_code, 201)
        sr_id = c_res.get_json()['stock_request']['stock_request_id']

        # demo_supplier rejects
        s_headers = self.get_headers('demo_supplier')
        r_res = self.client.patch(f'/api/stock-requests/{sr_id}/respond', headers=s_headers, json={
            'action': 'Reject',
            'notes': 'Out of production for this model.'
        })
        self.assertEqual(r_res.status_code, 200)
        self.assertEqual(r_res.get_json()['status'], 'Rejected')

        # Verify in DB
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT status, supplier_response_notes FROM "StockRequests" WHERE stock_request_id = %s', (sr_id,))
        row = cur.fetchone()
        self.assertEqual(row[0], 'Rejected')
        self.assertEqual(row[1], 'Out of production for this model.')
        cur.close()
        conn.close()

    # =========================================================================
    # PART I: FULL REGRESSION TEST (Steps 1–6)
    # =========================================================================
    def test_10_regression_step1_products_inventory(self):
        """Regression: Products and Inventory APIs continue functioning."""
        headers = self.get_headers('demo_manager')
        p_res = self.client.get('/api/products/', headers=headers)
        self.assertEqual(p_res.status_code, 200)
        self.assertIn('products', p_res.get_json())

        i_res = self.client.get('/api/inventory/', headers=headers)
        self.assertEqual(i_res.status_code, 200)
        self.assertIn('inventory', i_res.get_json())

    def test_11_regression_step2_suppliers(self):
        """Regression: Suppliers APIs continue functioning."""
        headers = self.get_headers('demo_manager')
        s_res = self.client.get('/api/suppliers/', headers=headers)
        self.assertEqual(s_res.status_code, 200)
        self.assertIn('suppliers', s_res.get_json())

    def test_12_regression_step3_purchase_orders(self):
        """Regression: Purchase Orders module remains isolated and functional."""
        headers = self.get_headers('demo_manager')
        po_res = self.client.get('/api/purchase-orders/', headers=headers)
        self.assertEqual(po_res.status_code, 200)
        self.assertIn('purchase_orders', po_res.get_json())

    def test_13_regression_step4_quotations(self):
        """Regression: Supplier Quotations module continues functioning."""
        headers = self.get_headers('demo_manager')
        q_res = self.client.get('/api/quotations/', headers=headers)
        self.assertEqual(q_res.status_code, 200)
        self.assertIn('quotations', q_res.get_json())

    def test_14_regression_step5_shipments(self):
        """Regression: Shipments module continues functioning."""
        headers = self.get_headers('demo_manager')
        sh_res = self.client.get('/api/shipments/', headers=headers)
        self.assertEqual(sh_res.status_code, 200)
        self.assertIn('shipments', sh_res.get_json())

    def test_15_regression_step6_stock_transactions(self):
        """Regression: Stock transactions module continues functioning."""
        headers = self.get_headers('demo_manager')
        tx_res = self.client.get('/api/inventory/transactions', headers=headers)
        self.assertEqual(tx_res.status_code, 200)
        self.assertIn('transactions', tx_res.get_json())


if __name__ == '__main__':
    unittest.main()
