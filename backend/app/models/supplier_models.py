from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

@dataclass
class Supplier:
    id: str
    company_name: str
    contact_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    status: str = "active"

@dataclass
class StockRequestSummary:
    id: str
    request_number: str
    request_date: str
    items_summary: str
    quantity: int
    status: str

@dataclass
class PurchaseOrderSummary:
    id: str
    po_number: str
    order_date: str
    total_amount: float
    status: str

@dataclass
class PendingShipmentSummary:
    id: str
    po_number: str
    status: str
    expected_delivery: Optional[str] = None
    tracking_number: Optional[str] = None

@dataclass
class NotificationSummary:
    id: str
    title: str
    message: str
    created_at: str
    is_read: bool = False
    type: str = "info"

@dataclass
class DashboardSummaryCounts:
    pending_requests: int = 0
    pending_quotations: int = 0
    pending_purchase_orders: int = 0
    orders_to_ship: int = 0
    shipped_orders: int = 0
    delivered_orders: int = 0
