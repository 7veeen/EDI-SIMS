import os
import sys
import json
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.app.services.team2.supplier_dashboard_service import SupplierDashboardService
from backend.app.config.config import Config

@pytest.fixture
def client():
    """Create Flask test client."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/team2/supplier/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["status"] == "healthy"

def test_dashboard_full_endpoint_authorized(client):
    """Test full dashboard retrieval with supplier authentication."""
    headers = {
        "X-Supplier-Id": "sup-test-100",
        "X-User-Role": "supplier"
    }
    response = client.get("/api/team2/supplier/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "data" in data

    d = data["data"]
    assert "supplier" in d
    assert "summary_counts" in d
    assert "recent_stock_requests" in d
    assert "recent_purchase_orders" in d
    assert "pending_shipments" in d
    assert "recent_notifications" in d

    # Verify summary cards structure
    counts = d["summary_counts"]
    for key in [
        "pending_requests",
        "pending_quotations",
        "pending_purchase_orders",
        "orders_to_ship",
        "shipped_orders",
        "delivered_orders"
    ]:
        assert key in counts
        assert isinstance(counts[key], int)

def test_summary_cards_endpoint(client):
    """Test granular summary cards endpoint."""
    headers = {"X-Supplier-Id": "sup-test-100", "X-User-Role": "supplier"}
    response = client.get("/api/team2/supplier/summary-cards", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "pending_requests" in data["data"]
    assert "orders_to_ship" in data["data"]

def test_recent_stock_requests_endpoint(client):
    """Test granular recent stock requests endpoint."""
    headers = {"X-Supplier-Id": "sup-test-100", "X-User-Role": "supplier"}
    response = client.get("/api/team2/supplier/recent-stock-requests?limit=3", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_recent_purchase_orders_endpoint(client):
    """Test granular recent purchase orders endpoint."""
    headers = {"X-Supplier-Id": "sup-test-100", "X-User-Role": "supplier"}
    response = client.get("/api/team2/supplier/recent-purchase-orders", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_pending_shipments_endpoint(client):
    """Test granular pending shipments endpoint."""
    headers = {"X-Supplier-Id": "sup-test-100", "X-User-Role": "supplier"}
    response = client.get("/api/team2/supplier/pending-shipments", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_notifications_endpoint(client):
    """Test notifications endpoint."""
    headers = {"X-Supplier-Id": "sup-test-100", "X-User-Role": "supplier"}
    response = client.get("/api/team2/supplier/notifications", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_supplier_profile_endpoint(client):
    """Test profile endpoint."""
    headers = {"X-Supplier-Id": "sup-test-100", "X-User-Role": "supplier"}
    response = client.get("/api/team2/supplier/profile", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["id"] == "sup-test-100"

def test_rbac_unauthorized_role(client):
    """Test that unauthorized roles cannot access supplier data."""
    headers = {
        "X-Supplier-Id": "sup-test-100",
        "X-User-Role": "unauthorized_role"
    }
    response = client.get("/api/team2/supplier/dashboard", headers=headers)
    assert response.status_code == 401
    data = response.get_json()
    assert data["success"] is False

def test_rbac_cross_supplier_tampering(client):
    """Test that a supplier cannot spoof another supplier's ID in query params."""
    headers = {
        "X-Supplier-Id": "sup-supplier-a",
        "X-User-Role": "supplier"
    }
    # Attempting to access sup-supplier-b while authenticated as sup-supplier-a
    response = client.get("/api/team2/supplier/dashboard?supplier_id=sup-supplier-b", headers=headers)
    assert response.status_code == 403
    data = response.get_json()
    assert data["success"] is False
    assert "another supplier" in data["message"].lower()

def test_frontend_serving(client):
    """Test that frontend HTML is properly served at root / and /team2."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Supplier Dashboard" in response.data
    assert b"Pending Requests" in response.data

    response_team2 = client.get("/team2")
    assert response_team2.status_code == 200
    assert b"Supplier Dashboard" in response_team2.data

    response_index = client.get("/index.html")
    assert response_index.status_code == 200
    assert b"Supplier Dashboard" in response_index.data

    response_po_relative = client.get("/purchase-orders/index.html")
    assert response_po_relative.status_code == 200
    assert b"Supplier Dashboard" in response_po_relative.data
