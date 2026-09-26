import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from ...config.supabase_client import get_db_connection, get_supabase_client
from ...config.config import Config

logger = logging.getLogger(__name__)

class SupplierPurchaseOrderService:
    """
    Business logic service for Supplier Purchase Orders (Team 2).
    Connects to Supabase PostgreSQL to retrieve, view, accept, and reject POs.
    Strictly enforces supplier data isolation and validates status transitions.
    """

    @staticmethod
    def _parse_id(val: Any) -> Any:
        try:
            return int(val)
        except (ValueError, TypeError):
            if isinstance(val, str) and val.startswith("sup-"):
                num = val.replace("sup-", "").lstrip("0")
                if num.isdigit():
                    return int(num)
            return val

    @classmethod
    def _resolve_supplier_id(cls, cur, raw_id: Any) -> Optional[int]:
        """
        Resolves raw identifier (integer, string like 'sup-004', or user_id)
        to the exact integer supplier_id in the Suppliers table.
        """
        if raw_id is None:
            return None
        parsed = cls._parse_id(raw_id)
        try:
            cur.execute(
                """
                SELECT supplier_id FROM "Suppliers"
                WHERE supplier_id = %s OR user_id = %s OR CAST(supplier_id AS TEXT) = %s
                LIMIT 1;
                """,
                (parsed if isinstance(parsed, int) else -1,
                 parsed if isinstance(parsed, int) else -1,
                 str(raw_id))
            )
            row = cur.fetchone()
            if row:
                return int(row[0])
        except Exception as e:
            logger.warning(f"Error resolving supplier_id {raw_id}: {e}")

        if isinstance(parsed, int):
            return parsed
        return None

    @classmethod
    def get_purchase_orders(
        cls,
        supplier_id: Any,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all purchase orders assigned to the logged-in supplier.
        Supports filtering by status and search by PO ID.
        """
        conn = get_db_connection()
        if not conn:
            return []

        try:
            cur = conn.cursor()
            sid = cls._resolve_supplier_id(cur, supplier_id)
            if sid is None:
                cur.close()
                conn.close()
                return []

            query = """
                SELECT po.purchase_order_id,
                       po.order_date,
                       po.expected_delivery,
                       po.total_amount,
                       po.status,
                       COALESCE(po.supplier_response, 'Pending') as supplier_response,
                       po.supplier_response_date,
                       po.rejection_reason,
                       u.username as manager_name,
                       COUNT(poi.purchase_order_item_id) as item_count,
                       STRING_AGG(DISTINCT c.category_name, ', ') as categories
                FROM "PurchaseOrders" po
                LEFT JOIN "Users" u ON po.ordered_by = u.user_id
                LEFT JOIN "PurchaseOrderItems" poi ON po.purchase_order_id = poi.purchase_order_id
                LEFT JOIN "Products" p ON poi.product_id = p.product_id
                LEFT JOIN "Categories" c ON p.category_id = c.category_id
                WHERE po.supplier_id = %s
            """
            params = [sid]

            if status_filter and status_filter.lower() != "all":
                query += " AND (po.status ILIKE %s OR po.supplier_response ILIKE %s)"
                params.extend([f"%{status_filter}%", f"%{status_filter}%"])

            if search_query:
                query += " AND (CAST(po.purchase_order_id AS TEXT) ILIKE %s OR p.product_name ILIKE %s)"
                clean_search = f"%{search_query.strip()}%"
                params.extend([clean_search, clean_search])

            query += """
                GROUP BY po.purchase_order_id, po.order_date, po.expected_delivery,
                         po.total_amount, po.status, po.supplier_response,
                         po.supplier_response_date, po.rejection_reason, u.username
                ORDER BY po.order_date DESC, po.purchase_order_id DESC;
            """

            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            cur.close()
            conn.close()

            pos = []
            for r in rows:
                p_id = r[0]
                pos.append({
                    "id": p_id,
                    "po_number": f"PO-{p_id:04d}" if isinstance(p_id, int) else str(p_id),
                    "order_date": r[1].isoformat() if r[1] else "",
                    "expected_delivery": r[2].isoformat() if r[2] else "",
                    "total_amount": float(r[3]) if r[3] is not None else 0.0,
                    "status": r[4] or "Pending",
                    "supplier_response": r[5] or "Pending",
                    "supplier_response_date": r[6].isoformat() if r[6] else None,
                    "rejection_reason": r[7] or "",
                    "manager_name": r[8] or "Inventory Manager",
                    "item_count": r[9] or 0,
                    "categories": r[10] or "General Inventory"
                })
            return pos
        except Exception as e:
            logger.error(f"Error fetching purchase orders: {e}")
            if conn:
                conn.close()
            return []

    @classmethod
    def get_purchase_order_details(cls, supplier_id: Any, po_id: Any) -> Optional[Dict[str, Any]]:
        """
        Fetch full details of a specific PO along with line items.
        Enforces supplier authorization: returns None or raises error if PO belongs to another supplier.
        """
        p_id = cls._parse_id(po_id)
        conn = get_db_connection()
        if not conn:
            return None

        try:
            cur = conn.cursor()
            sid = cls._resolve_supplier_id(cur, supplier_id)

            # 1. Fetch PO Header
            cur.execute("""
                SELECT po.purchase_order_id,
                       po.supplier_id,
                       po.order_date,
                       po.expected_delivery,
                       po.total_amount,
                       po.status,
                       COALESCE(po.supplier_response, 'Pending') as supplier_response,
                       po.supplier_response_date,
                       po.rejection_reason,
                       u.username as manager_name,
                       u.email as manager_email,
                       s.supplier_name
                FROM "PurchaseOrders" po
                LEFT JOIN "Users" u ON po.ordered_by = u.user_id
                LEFT JOIN "Suppliers" s ON po.supplier_id = s.supplier_id
                WHERE po.purchase_order_id = %s;
            """, (p_id,))
            po_row = cur.fetchone()

            if not po_row:
                cur.close()
                conn.close()
                return None  # PO not found

            # Verify Supplier Authorization
            actual_supplier_id = po_row[1]
            if sid is not None and str(actual_supplier_id) != str(sid):
                cur.close()
                conn.close()
                raise PermissionError("Access denied: You are not authorized to view this purchase order.")

            # 2. Fetch PO Items
            cur.execute("""
                SELECT poi.purchase_order_item_id,
                       poi.product_id,
                       p.product_name,
                       p.sku,
                       c.category_name,
                       poi.quantity,
                       poi.unit_price,
                       poi.subtotal
                FROM "PurchaseOrderItems" poi
                JOIN "Products" p ON poi.product_id = p.product_id
                LEFT JOIN "Categories" c ON p.category_id = c.category_id
                WHERE poi.purchase_order_id = %s
                ORDER BY poi.purchase_order_item_id ASC;
            """, (p_id,))
            item_rows = cur.fetchall()
            cur.close()
            conn.close()

            items = []
            for ir in item_rows:
                items.append({
                    "item_id": ir[0],
                    "product_id": ir[1],
                    "product_name": ir[2],
                    "sku": ir[3] or "N/A",
                    "category": ir[4] or "General",
                    "quantity": ir[5],
                    "unit_price": float(ir[6]),
                    "subtotal": float(ir[7])
                })

            return {
                "id": po_row[0],
                "po_number": f"PO-{po_row[0]:04d}" if isinstance(po_row[0], int) else str(po_row[0]),
                "supplier_id": po_row[1],
                "order_date": po_row[2].isoformat() if po_row[2] else "",
                "expected_delivery": po_row[3].isoformat() if po_row[3] else "",
                "total_amount": float(po_row[4]) if po_row[4] is not None else 0.0,
                "status": po_row[5] or "Pending",
                "supplier_response": po_row[6] or "Pending",
                "supplier_response_date": po_row[7].isoformat() if po_row[7] else None,
                "rejection_reason": po_row[8] or "",
                "manager_name": po_row[9] or "Inventory Manager",
                "manager_email": po_row[10] or "",
                "supplier_name": po_row[11] or "",
                "items": items
            }
        except PermissionError:
            raise
        except Exception as e:
            logger.error(f"Error fetching PO details: {e}")
            if conn:
                conn.close()
            return None

    @classmethod
    def accept_purchase_order(cls, supplier_id: Any, po_id: Any) -> Dict[str, Any]:
        """
        Accept a purchase order by the authenticated supplier.
        Validates ownership and allowed transitions.
        """
        p_id = cls._parse_id(po_id)
        conn = get_db_connection()
        if not conn:
            raise RuntimeError("Database connection unavailable")

        try:
            cur = conn.cursor()
            sid = cls._resolve_supplier_id(cur, supplier_id)

            # Check existing PO and ownership
            cur.execute("""
                SELECT purchase_order_id, supplier_id, status, supplier_response
                FROM "PurchaseOrders"
                WHERE purchase_order_id = %s;
            """, (p_id,))
            row = cur.fetchone()

            if not row:
                cur.close()
                conn.close()
                raise ValueError("Purchase order not found")

            if sid is not None and str(row[1]) != str(sid):
                cur.close()
                conn.close()
                raise PermissionError("Access denied: You are not authorized to respond to this purchase order.")

            current_response = (row[3] or "Pending").strip().capitalize()
            if current_response == "Accepted":
                cur.close()
                conn.close()
                raise ValueError("This purchase order has already been accepted.")
            if current_response == "Rejected":
                cur.close()
                conn.close()
                raise ValueError("Cannot accept an already rejected purchase order.")

            # Update PO to Accepted
            cur.execute("""
                UPDATE "PurchaseOrders"
                SET supplier_response = 'Accepted',
                    supplier_response_date = NOW(),
                    status = 'Accepted'
                WHERE purchase_order_id = %s;
            """, (p_id,))
            conn.commit()
            cur.close()
            conn.close()

            # Return refreshed details
            return cls.get_purchase_order_details(supplier_id, po_id)
        except (ValueError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"Error accepting purchase order: {e}")
            if conn:
                conn.rollback()
                conn.close()
            raise RuntimeError(f"Database error during acceptance: {e}")

    @classmethod
    def reject_purchase_order(cls, supplier_id: Any, po_id: Any, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Reject a purchase order by the authenticated supplier with optional reason.
        Validates ownership and allowed transitions.
        """
        p_id = cls._parse_id(po_id)
        conn = get_db_connection()
        if not conn:
            raise RuntimeError("Database connection unavailable")

        try:
            cur = conn.cursor()
            sid = cls._resolve_supplier_id(cur, supplier_id)

            # Check existing PO and ownership
            cur.execute("""
                SELECT purchase_order_id, supplier_id, status, supplier_response
                FROM "PurchaseOrders"
                WHERE purchase_order_id = %s;
            """, (p_id,))
            row = cur.fetchone()

            if not row:
                cur.close()
                conn.close()
                raise ValueError("Purchase order not found")

            if sid is not None and str(row[1]) != str(sid):
                cur.close()
                conn.close()
                raise PermissionError("Access denied: You are not authorized to respond to this purchase order.")

            current_response = (row[3] or "Pending").strip().capitalize()
            if current_response == "Accepted":
                cur.close()
                conn.close()
                raise ValueError("Cannot reject a purchase order that has already been accepted.")
            if current_response == "Rejected":
                cur.close()
                conn.close()
                raise ValueError("This purchase order has already been rejected.")

            # Update PO to Rejected
            cur.execute("""
                UPDATE "PurchaseOrders"
                SET supplier_response = 'Rejected',
                    supplier_response_date = NOW(),
                    rejection_reason = %s,
                    status = 'Rejected'
                WHERE purchase_order_id = %s;
            """, (reason or "Supplier unable to fulfill order at this time", p_id))
            conn.commit()
            cur.close()
            conn.close()

            return cls.get_purchase_order_details(supplier_id, po_id)
        except (ValueError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"Error rejecting purchase order: {e}")
            if conn:
                conn.rollback()
                conn.close()
            raise RuntimeError(f"Database error during rejection: {e}")

    @classmethod
    def get_all_suppliers(cls) -> List[Dict[str, Any]]:
        """Fetch all registered active suppliers for user switching/authentication."""
        conn = get_db_connection()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT supplier_id, user_id, supplier_name, contact_person, email, phone, status
                FROM "Suppliers"
                ORDER BY supplier_id ASC;
            """)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [
                {
                    "supplier_id": r[0],
                    "id": str(r[0]),
                    "user_id": r[1],
                    "company_name": r[2],
                    "supplier_name": r[2],
                    "contact_person": r[3] or "",
                    "email": r[4] or "",
                    "phone": r[5] or "",
                    "status": r[6] or "Active"
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Error fetching suppliers list: {e}")
            if conn:
                conn.close()
            return []
