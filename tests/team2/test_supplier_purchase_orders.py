import os
import sys
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.app.services.team2.supplier_po_service import SupplierPurchaseOrderService

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_get_purchase_orders_list(client):
    """Test retrieving purchase orders for supplier 4."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    res = client.get("/api/team2/supplier/purchase-orders", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0

    po = data["data"][0]
    assert "id" in po
    assert "po_number" in po
    assert "order_date" in po
    assert "total_amount" in po
    assert "status" in po
    assert "supplier_response" in po

def test_search_and_filter_po(client):
    """Test status filter on purchase orders."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    # Get all orders first
    res_all = client.get("/api/team2/supplier/purchase-orders", headers=headers)
    assert res_all.status_code == 200
    all_data = res_all.get_json()["data"]
    assert len(all_data) > 0

    first_po = all_data[0]
    first_po_id = first_po["id"]
    first_po_status = first_po["status"]

    # Filter by that status
    res = client.get(f"/api/team2/supplier/purchase-orders?status={first_po_status}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1

    # Search by PO ID
    res_search = client.get(f"/api/team2/supplier/purchase-orders?search={first_po_id}", headers=headers)
    assert res_search.status_code == 200
    search_data = res_search.get_json()
    assert len(search_data["data"]) >= 1

def test_get_purchase_order_details(client):
    """Test retrieving details and line items of a specific PO."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    
    # Get first PO id
    list_res = client.get("/api/team2/supplier/purchase-orders", headers=headers)
    po_id = list_res.get_json()["data"][0]["id"]

    res = client.get(f"/api/team2/supplier/purchase-orders/{po_id}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    po = data["data"]
    assert po["id"] == po_id
    assert "items" in po
    assert isinstance(po["items"], list)
    assert len(po["items"]) > 0

    item = po["items"][0]
    assert "product_name" in item
    assert "quantity" in item
    assert "unit_price" in item
    assert "subtotal" in item

def test_accept_purchase_order(client):
    """Test accepting a pending purchase order."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}

    # Find a pending order
    list_res = client.get("/api/team2/supplier/purchase-orders?status=Pending", headers=headers)
    pending_orders = list_res.get_json()["data"]
    if pending_orders:
        po_id = pending_orders[0]["id"]
        res = client.post(f"/api/team2/supplier/purchase-orders/{po_id}/accept", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["data"]["supplier_response"] == "Accepted"
        assert data["data"]["status"] == "Accepted"

def test_reject_purchase_order(client):
    """Test rejecting a purchase order with reason."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}

    # Find another pending order
    list_res = client.get("/api/team2/supplier/purchase-orders?status=Pending", headers=headers)
    pending_orders = list_res.get_json()["data"]
    if pending_orders:
        po_id = pending_orders[0]["id"]
        payload = {"reason": "Temporary stock shortage in warehouse"}
        res = client.post(f"/api/team2/supplier/purchase-orders/{po_id}/reject", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["data"]["supplier_response"] == "Rejected"
        assert data["data"]["status"] == "Rejected"
        assert data["data"]["rejection_reason"] == "Temporary stock shortage in warehouse"

def test_unauthorized_po_access(client):
    """Test that supplier 5 cannot access supplier 4's PO."""
    headers_sup4 = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    list_res = client.get("/api/team2/supplier/purchase-orders", headers=headers_sup4)
    po_id = list_res.get_json()["data"][0]["id"]

    # Attempt access as supplier 5
    headers_sup5 = {"X-Supplier-Id": "5", "X-User-Role": "supplier"}
    res = client.get(f"/api/team2/supplier/purchase-orders/{po_id}", headers=headers_sup5)
    assert res.status_code == 403
    data = res.get_json()
    assert data["success"] is False
    assert "access denied" in data["message"].lower()

def test_po_not_found(client):
    """Test 404 on non-existent PO."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    res = client.get("/api/team2/supplier/purchase-orders/999999", headers=headers)
    assert res.status_code == 404
    data = res.get_json()
    assert data["success"] is False

def test_frontend_serving(client):
    """Test that purchase-orders.html is served."""
    res = client.get("/purchase-orders")
    assert res.status_code == 200
    assert b"Purchase Orders" in res.data
    assert b"Assigned Purchase Orders" in res.data

    res_html = client.get("/purchase-orders.html")
    assert res_html.status_code == 200
    assert b"Purchase Orders" in res_html.data

    res_team2 = client.get("/team2/purchase-orders")
    assert res_team2.status_code == 200
    assert b"Purchase Orders" in res_team2.data

def test_supplier_specific_data_isolation(client):
    """Test that Supplier 4 and Supplier 5 see strictly their own POs and no cross-leakage."""
    headers_sup4 = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    headers_sup5 = {"X-Supplier-Id": "5", "X-User-Role": "supplier"}

    res4 = client.get("/api/team2/supplier/purchase-orders", headers=headers_sup4)
    assert res4.status_code == 200
    data4 = res4.get_json()["data"]

    res5 = client.get("/api/team2/supplier/purchase-orders", headers=headers_sup5)
    assert res5.status_code == 200
    data5 = res5.get_json()["data"]

    ids4 = {po["id"] for po in data4}
    ids5 = {po["id"] for po in data5}

    # Verify each supplier has records and the sets are mutually disjoint
    assert len(ids4) > 0
    assert len(ids5) > 0
    assert ids4.isdisjoint(ids5), f"Data leakage detected! Supplier 4 and 5 share PO IDs: {ids4.intersection(ids5)}"

def test_get_suppliers_list(client):
    """Test retrieving all registered suppliers."""
    res = client.get("/api/team2/supplier/purchase-orders/suppliers")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 2
    supplier_ids = [s["supplier_id"] for s in data["data"]]
    assert 4 in supplier_ids
    assert 5 in supplier_ids

def test_current_supplier_profile(client):
    """Test retrieving authenticated supplier profile."""
    headers = {"X-Supplier-Id": "5", "X-User-Role": "supplier"}
    res = client.get("/api/team2/supplier/purchase-orders/current-supplier", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["id"] == "5"
    assert "Demo Supplier" in data["data"]["company_name"]
