import os
import sys
import pytest
from pathlib import Path
from datetime import datetime, date, timedelta

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.app.services.team2.supplier_shipment_service import SupplierShipmentService

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_get_shipments_list(client):
    """Test retrieving active shipments for Supplier 4."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    res = client.get("/api/team2/supplier/shipments", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

    if len(data["data"]) > 0:
        shipment = data["data"][0]
        assert "shipment_id" in shipment
        assert "shipment_number" in shipment
        assert "purchase_order_id" in shipment
        assert "carrier" in shipment
        assert "status" in shipment

def test_get_orders_ready_to_ship(client):
    """Test retrieving orders available to be marked ready for shipping."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    res = client.get("/api/team2/supplier/shipments/ready-to-ship", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_get_completed_shipments(client):
    """Test retrieving completed (Delivered) shipments."""
    headers = {"X-Supplier-Id": "5", "X-User-Role": "supplier"}
    res = client.get("/api/team2/supplier/shipments/completed", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0

    comp = data["data"][0]
    assert comp["status"] == "Delivered"
    assert "delivered_at" in comp
    assert "transit_duration_days" in comp

def test_get_fulfillment_stats(client):
    """Test aggregated fulfillment summary stats."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    res = client.get("/api/team2/supplier/shipments/stats", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    stats = data["data"]
    assert "ready_for_shipment_count" in stats
    assert "active_shipments_count" in stats
    assert "completed_shipments_count" in stats
    assert "total_previous_pos" in stats
    assert "total_previous_quotations" in stats
    assert "on_time_delivery_rate" in stats

def test_mark_order_ready_for_shipment(client):
    """Test marking an accepted purchase order ready for shipment."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    payload = {
        "purchase_order_id": 4,
        "notes": "Quality check passed, goods packaged and ready for pickup"
    }
    res = client.post("/api/team2/supplier/shipments/ready", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["purchase_order_id"] == 4
    assert data["data"]["status"] == "Ready for Shipment"

def test_enter_shipment_details(client):
    """Test entering shipment details: carrier, tracking number, package count, notes."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    payload = {
        "purchase_order_id": 4,
        "carrier": "BlueDart Express",
        "tracking_number": "BD-TEST-998877",
        "shipping_method": "Express Cargo",
        "package_count": 2,
        "total_weight": 8.5,
        "shipping_notes": "Handle with care, delicate optics.",
        "expected_delivery": (date.today() + timedelta(days=3)).isoformat()
    }
    res = client.post("/api/team2/supplier/shipments/details", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["carrier"] == "BlueDart Express"
    assert data["data"]["tracking_number"] == "BD-TEST-998877"
    assert data["data"]["package_count"] == 2

def test_update_expected_delivery(client):
    """Test updating expected delivery date on a shipment."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    new_delivery = (date.today() + timedelta(days=4)).isoformat()
    payload = {
        "expected_delivery": new_delivery,
        "reason": "Expedited transit routing via central hub"
    }
    res = client.put("/api/team2/supplier/shipments/1/expected-delivery", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["new_expected_delivery"] == new_delivery

def test_update_shipment_status_and_mark_shipped(client):
    """Test updating shipment status to In Transit and Shipped."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    # 1. Mark shipped
    shipped_payload = {
        "carrier": "BlueDart Express",
        "tracking_number": "BD-789214582",
        "expected_delivery": (date.today() + timedelta(days=2)).isoformat(),
        "notes": "Package dispatched from warehouse"
    }
    res_shipped = client.post("/api/team2/supplier/shipments/1/mark-shipped", json=shipped_payload, headers=headers)
    assert res_shipped.status_code == 200
    assert res_shipped.get_json()["data"]["status"] == "Shipped"

    # 2. Update status to In Transit
    transit_payload = {
        "status": "In Transit",
        "location": "Regional Hub Mumbai",
        "notes": "Scanned at sorting hub"
    }
    res_transit = client.put("/api/team2/supplier/shipments/1/status", json=transit_payload, headers=headers)
    assert res_transit.status_code == 200
    assert res_transit.get_json()["data"]["status"] == "In Transit"

def test_mark_as_delivered(client):
    """Test marking shipment as delivered."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    payload = {
        "notes": "Delivered and signed by receiving warehouse manager"
    }
    res = client.post("/api/team2/supplier/shipments/1/mark-delivered", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["status"] == "Delivered"

def test_previous_purchase_orders(client):
    """Test previous purchase orders endpoint."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    res = client.get("/api/team2/supplier/history/purchase-orders", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0

    po = data["data"][0]
    assert "purchase_order_id" in po
    assert "total_amount" in po
    assert "items_summary" in po

def test_previous_quotations(client):
    """Test previous quotations endpoint."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    res = client.get("/api/team2/supplier/history/quotations", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0

    q = data["data"][0]
    assert "quotation_id" in q
    assert "product_name" in q
    assert "quoted_price" in q
    assert "quantity" in q
    assert "status" in q

def test_order_status_history_timeline(client):
    """Test order status history timeline endpoint."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    res = client.get("/api/team2/supplier/history/order/4", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0

    event = data["data"][0]
    assert "history_id" in event
    assert "status" in event
    assert "action" in event
    assert "created_at" in event

def test_rbac_supplier_isolation(client):
    """Test that Supplier 4 cannot access or mutate Supplier 5's shipment."""
    headers = {"X-Supplier-Id": "4", "X-User-Role": "supplier"}
    # Shipment 2 belongs to Supplier 5
    res = client.get("/api/team2/supplier/shipments/2", headers=headers)
    assert res.status_code == 404

    payload = {"status": "In Transit"}
    res_mutate = client.put("/api/team2/supplier/shipments/2/status", json=payload, headers=headers)
    assert res_mutate.status_code == 403
