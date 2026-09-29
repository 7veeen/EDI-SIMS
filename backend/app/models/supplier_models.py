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

@dataclass
class Shipment:
    id: str
    shipment_number: str
    purchase_order_id: int
    supplier_id: int
    carrier: str
    tracking_number: Optional[str] = None
    shipping_method: str = "Standard Ground"
    status: str = "Ready for Shipment"
    package_count: int = 1
    total_weight: Optional[float] = None
    shipping_notes: Optional[str] = None
    expected_delivery: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    created_at: Optional[str] = None

@dataclass
class OrderStatusHistoryEntry:
    history_id: int
    purchase_order_id: int
    shipment_id: Optional[int]
    status: str
    action: str
    changed_by: str
    created_at: str
    previous_status: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

@dataclass
class QuotationHistoryItem:
    quotation_id: int
    supplier_id: int
    product_id: int
    product_name: str
    sku: Optional[str]
    quoted_price: float
    quantity: int
    total_amount: float
    quotation_date: str
    valid_until: Optional[str]
    status: str

