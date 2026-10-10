import csv
import io
from datetime import datetime
from decimal import Decimal

from app.extensions import get_db_connection


def check_inventory_status():
    """
    Checks the status of the Inventory module in the SystemStatus table.
    Returns:
        (status_info_dict, None, 200) on success,
        (None, {"error": "..."}, 404/500) on error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT status, progress, message, updated_at
            FROM "SystemStatus"
            WHERE module_name = 'Inventory'
        ''')
        row = cursor.fetchone()
        if row is None:
            return None, {"error": "Inventory status not found"}, 404

        status_info = {
            "status": row[0],
            "progress": row[1],
            "message": row[2],
            "updated_at": row[3]
        }
        return status_info, None, 200
    except Exception:
        return None, {"error": "Database error while checking inventory status"}, 500
    finally:
        cursor.close()
        conn.close()


def get_reports_metadata():
    """
    Retrieves the list of generated reports metadata from the Reports table.
    Returns:
        (reports_list, None, 200) on success,
        (None, {"error": "..."}, 500) on error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT report_id, report_name, report_type, generated_by, generated_on
            FROM "Reports"
            ORDER BY report_id DESC
        ''')
        rows = cursor.fetchall()
        reports = []
        for row in rows:
            reports.append({
                "report_id": row[0],
                "report_name": row[1],
                "report_type": row[2],
                "generated_by": row[3],
                "generated_on": row[4]
            })
        return reports, None, 200
    except Exception:
        return None, {"error": "Database error while fetching reports list"}, 500
    finally:
        cursor.close()
        conn.close()


def fetch_inventory_report_data():
    """
    Queries current live inventory items with product details, category, available stock,
    reorder level, unit price, and calculated inventory value.
    Validates that the Inventory module is in 'READY' status first.
    Returns:
        (report_data_list, None, 200) on success,
        (None, error_dict, 423/404/500) on lock or error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check whether inventory module is ready
        cursor.execute('''
            SELECT status, progress, message
            FROM "SystemStatus"
            WHERE module_name = 'Inventory'
        ''')
        status_row = cursor.fetchone()
        if status_row is None:
            return None, {"error": "Inventory status not found"}, 404

        inventory_status, progress, message = status_row[0], status_row[1], status_row[2]

        if inventory_status != "READY":
            return None, {
                "error": "Report generation locked",
                "status": inventory_status,
                "progress": progress,
                "message": message
            }, 423

        cursor.execute('''
            SELECT
                p.product_id,
                p.product_name,
                p.sku,
                COALESCE(c.category_name, 'Uncategorized') AS category_name,
                COALESCE(i.quantity_available, 0) AS quantity_available,
                COALESCE(p.reorder_level, 0) AS reorder_level,
                COALESCE(p.selling_price, 0.00) AS selling_price,
                (COALESCE(i.quantity_available, 0) * COALESCE(p.selling_price, 0.00)) AS inventory_value,
                COALESCE(p.status, 'Unknown') AS status,
                i.last_updated
            FROM public."Products" p
            LEFT JOIN public."Categories" c
                ON p.category_id = c.category_id
            LEFT JOIN public."Inventory" i
                ON p.product_id = i.product_id
            ORDER BY p.product_id ASC
        ''')

        rows = cursor.fetchall()
        report_data = []

        for row in rows:
            qty = int(row[4])
            reorder = int(row[5])
            unit_price = Decimal(str(row[6]))
            inv_value = Decimal(str(row[7]))
            stock_status = "LOW STOCK" if qty <= reorder else "IN STOCK"

            report_data.append({
                "product_id": row[0],
                "product_name": row[1],
                "sku": row[2],
                "category_name": row[3],
                "quantity_available": qty,
                "reorder_level": reorder,
                "unit_price": float(unit_price),
                "inventory_value": float(inv_value),
                "status": row[8],
                "stock_status": stock_status,
                "last_updated": row[9]
            })

        return report_data, None, 200

    except Exception:
        return None, {"error": "Database error while fetching inventory data"}, 500
    finally:
        cursor.close()
        conn.close()


def generate_inventory_report_record(report_name, report_type, generated_by):
    """
    Creates a new entry in the Reports metadata table and retrieves the report data.
    Returns:
        (result_dict, None, 201) on success,
        (None, error_dict, 423/400/500) on failure.
    """
    # Verify status and fetch current report items
    report_data, error, status_code = fetch_inventory_report_data()
    if error:
        return None, error, status_code

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO "Reports"
            (
                report_name,
                report_type,
                generated_by
            )
            VALUES (%s, %s, %s)
            RETURNING report_id, report_name, report_type, generated_by, generated_on
        ''', (
            report_name,
            report_type,
            generated_by
        ))
        row = cursor.fetchone()
        conn.commit()

        result = {
            "message": "Report generated successfully",
            "report": {
                "report_id": row[0],
                "report_name": row[1],
                "report_type": row[2],
                "generated_by": row[3],
                "generated_on": row[4]
            },
            "data": report_data
        }
        return result, None, 201

    except Exception:
        conn.rollback()
        return None, {"error": "Failed to create report record"}, 500
    finally:
        cursor.close()
        conn.close()


DANGEROUS_FORMULA_PREFIXES = ('=', '+', '-', '@')


def sanitize_csv_cell(value):
    """
    Sanitizes untrusted text values to prevent CSV / Formula Injection (CWE-1236).
    If a text value (after stripping any leading whitespace or control characters such as
    spaces, tabs, carriage returns, newlines) begins with '=', '+', '-', or '@',
    it is prepended with a single quote (') so spreadsheet applications (Excel, Calc, Sheets)
    treat it as literal text rather than executing it as an expression or macro.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        return value
    if not value:
        return value

    stripped = value.lstrip(' \t\r\n\v\f')
    if stripped and stripped.startswith(DANGEROUS_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def generate_inventory_csv_export(report_type="Inventory"):
    """
    Generates a live inventory report formatted as RFC 4180 compliant CSV with UTF-8 BOM encoding.
    Returns:
        ((csv_bytes, filename), None, 200) on success,
        (None, error_dict, 423/404/500) on failure.
    """
    report_data, error, status_code = fetch_inventory_report_data()
    if error:
        return None, error, status_code

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='\r\n')

    # Column headers
    writer.writerow([
        "Product ID",
        "Product Name",
        "SKU",
        "Category",
        "Available Quantity",
        "Reorder Level",
        "Unit Price",
        "Inventory Value",
        "Stock Status",
        "Status",
        "Last Updated"
    ])

    for item in report_data:
        last_updated_str = "N/A"
        if item.get("last_updated"):
            try:
                last_updated_str = item["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
            except AttributeError:
                last_updated_str = str(item["last_updated"])

        writer.writerow([
            item["product_id"],
            sanitize_csv_cell(item["product_name"]),
            sanitize_csv_cell(item["sku"]),
            sanitize_csv_cell(item["category_name"]),
            item["quantity_available"],
            item["reorder_level"],
            f"{item['unit_price']:.2f}",
            f"{item['inventory_value']:.2f}",
            item["stock_status"],
            sanitize_csv_cell(item["status"]),
            last_updated_str
        ])

    csv_text = output.getvalue()
    csv_bytes = csv_text.encode('utf-8-sig')

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"current_inventory_report_{timestamp_str}.csv"

    return (csv_bytes, filename), None, 200
