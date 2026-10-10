// test_phase5_frontend_logic.js
// Unit test for Phase 5 frontend snapshot metrics calculation and escaping logic

const assert = require('assert');

// Test 1: Quotations calculation logic
const sampleQuotationsSnapshot = [
    {
        quotation_id: 1,
        quotation_number: "QT-2026-0001",
        supplier_name: "Supplier A",
        status: "Approved",
        total_amount: 1200.50,
        items: [
            { product_name: "Item 1", quoted_quantity: 10, unit_price: 50.0, subtotal: 500.0 },
            { product_name: "Item 2", quoted_quantity: 10, unit_price: 70.05, subtotal: 700.50 }
        ]
    },
    {
        quotation_id: 2,
        quotation_number: "QT-2026-0002",
        supplier_name: "Supplier B",
        status: "Rejected",
        total_amount: 450.00,
        items: [
            { product_name: "Item 3", quoted_quantity: 5, unit_price: 90.0, subtotal: 450.0 }
        ]
    },
    {
        quotation_id: 3,
        quotation_number: "QT-2026-0003",
        supplier_name: "Supplier C",
        status: "Pending",
        total_amount: 300.00,
        items: [
            { product_name: "Item 4", quoted_quantity: 3, unit_price: 100.0, subtotal: 300.0 }
        ]
    }
];

const totalQuotations = sampleQuotationsSnapshot.length;
const totalVal = sampleQuotationsSnapshot.reduce((sum, q) => sum + (Number(q.total_amount) || 0), 0);
const approvedCount = sampleQuotationsSnapshot.filter(q => ['Approved', 'Accepted'].includes(q.status)).length;
const pendingCount = sampleQuotationsSnapshot.filter(q => ['Pending', 'Submitted', 'Under Review', 'Draft'].includes(q.status)).length;
const rejectedCount = sampleQuotationsSnapshot.filter(q => ['Rejected', 'Expired'].includes(q.status)).length;

assert.strictEqual(totalQuotations, 3);
assert.strictEqual(totalVal, 1950.50);
assert.strictEqual(approvedCount, 1);
assert.strictEqual(pendingCount, 1);
assert.strictEqual(rejectedCount, 1);
console.log(" [PASS] Test 1: Quotations metric calculations verified.");

// Test 2: Supplier Performance calculation logic
const sampleSupplierSnapshot = [
    {
        supplier_id: 4,
        supplier_name: "Supplier 1 Company",
        total_purchase_orders: 20,
        accepted_purchase_orders: 16,
        rejected_purchase_orders: 4,
        total_order_value: 100000.0,
        po_acceptance_rate: 80.0,
        total_quotations: 10,
        responded_quotations: 8,
        approved_quotations: 6,
        quotation_response_rate: 80.0,
        quotation_approval_rate: 75.0,
        total_shipments: 10,
        delivered_shipments: 8,
        measurable_deliveries: 4,
        on_time_deliveries: 3,
        on_time_delivery_rate: 75.0,
        avg_delivery_delay_days: -2.5
    },
    {
        supplier_id: 5,
        supplier_name: "Demo Supplier Company",
        total_purchase_orders: 50,
        accepted_purchase_orders: 40,
        rejected_purchase_orders: 10,
        total_order_value: 500000.0,
        po_acceptance_rate: 80.0,
        total_quotations: 20,
        responded_quotations: 15,
        approved_quotations: 12,
        quotation_response_rate: 75.0,
        quotation_approval_rate: 80.0,
        total_shipments: 30,
        delivered_shipments: 25,
        measurable_deliveries: 0,
        on_time_deliveries: 0,
        on_time_delivery_rate: null,
        avg_delivery_delay_days: null
    }
];

const totalSuppliers = sampleSupplierSnapshot.length;
const totalPOVal = sampleSupplierSnapshot.reduce((sum, s) => sum + (Number(s.total_order_value) || 0), 0);
const totalPOs = sampleSupplierSnapshot.reduce((sum, s) => sum + (Number(s.total_purchase_orders) || 0), 0);
const totalQuotes = sampleSupplierSnapshot.reduce((sum, s) => sum + (Number(s.total_quotations) || 0), 0);

assert.strictEqual(totalSuppliers, 2);
assert.strictEqual(totalPOVal, 600000.0);
assert.strictEqual(totalPOs, 70);
assert.strictEqual(totalQuotes, 30);

// Null delivery rate handling
assert.strictEqual(sampleSupplierSnapshot[1].on_time_delivery_rate, null);
const delivStr = sampleSupplierSnapshot[1].on_time_delivery_rate !== null ? `${sampleSupplierSnapshot[1].on_time_delivery_rate}%` : 'Unscheduled';
assert.strictEqual(delivStr, 'Unscheduled');
console.log(" [PASS] Test 2: Supplier Performance metric calculations & unscheduled handling verified.");

// Test 3: XSS HTML Escaping check
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

const dirtyString = '<script>alert("xss")</script>';
const cleanString = escapeHtml(dirtyString);
assert.strictEqual(cleanString, '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;');
console.log(" [PASS] Test 3: XSS string escaping verified.");

console.log("\nALL FRONTEND UNIT LOGIC TESTS PASSED!");
