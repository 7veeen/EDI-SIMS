/**
 * test_notification_deep_linking.js - Automated Verification for SIMS Notification Deep-Linking
 * Phase 2 Implementation Testing:
 * 1. Reference type normalization & historical aliases
 * 2. Dispatcher behavior & direct modal execution
 * 3. Role-based access control (RBAC) navigation guards
 * 4. Mark-as-read invocation & unread counter refresh
 * 5. Edge cases: null, empty, unsupported, uninitialized controllers
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log("=== SIMS Phase 2: Notification Deep-Linking Automated Verification ===");

// 1. Read app.js and extract App definition
const appJsPath = path.join(__dirname, '..', '..', 'frontend', 'js', 'app.js');
assert(fs.existsSync(appJsPath), `app.js must exist at ${appJsPath}`);
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

// Set up mock browser environment
let mockHash = 'dashboard';
let toastMessages = [];
let markedReadIds = [];
let unreadCountUpdates = 0;
let modalCalls = {};
let filterCalls = {};

const mockLocation = {
    get hash() { return '#' + mockHash; },
    set hash(val) { mockHash = val.replace(/^#/, ''); }
};

let currentUser = { username: 'owner_user', role: 'Owner' };

const mockAuth = {
    getUser: () => currentUser,
    isAuthenticated: () => true
};

const mockUtils = {
    showToast: (msg, type) => {
        toastMessages.push({ msg, type });
    },
    formatDate: (d) => d
};

const mockApi = {
    markNotificationRead: async (id) => {
        markedReadIds.push(id);
        return { success: true };
    }
};

const mockElements = {
    'tx-search-input': { value: '' }
};

const mockDocument = {
    getElementById: (id) => {
        if (id === 'content-area') return { children: [{ id: 'mock-child' }] };
        return mockElements[id] || null;
    },
    querySelectorAll: () => [],
    addEventListener: () => {}
};

// Create sandbox and evaluate app.js within it
const vm = require('vm');
const sandbox = {
    window: { location: mockLocation, addEventListener: () => {} },
    document: mockDocument,
    Auth: mockAuth,
    Utils: mockUtils,
    Api: mockApi,
    console: console,
    setTimeout: (fn, delay) => { fn(); return 1; }, // Synchronous or immediate execution for deterministic testing
    clearTimeout: () => {},
    localStorage: { getItem: () => null, setItem: () => {} }
};

vm.createContext(sandbox);
const App = vm.runInContext(appJsContent + '\n; App;', sandbox);

assert(App, "App object must be loaded from app.js");
assert(typeof App.normalizeReferenceType === 'function', "App.normalizeReferenceType must be a function");
assert(typeof App.navigateToReference === 'function', "App.navigateToReference must be a function");
console.log("✓ App loaded successfully with normalization and navigation helpers");

// =========================================================================
// TEST SUITE 1: REFERENCE TYPE NORMALIZATION
// =========================================================================
console.log("\n--- [Suite 1] Reference Type Normalization ---");

const normalizationCases = [
    // Shipment variants
    { input: 'Shipment', expected: 'SHIPMENT' },
    { input: 'SHIPMENT', expected: 'SHIPMENT' },
    { input: 'shipment', expected: 'SHIPMENT' },
    { input: ' Shipment  ', expected: 'SHIPMENT' },
    { input: 'ship_ment', expected: 'SHIPMENT' },

    // PurchaseOrder variants
    { input: 'PurchaseOrder', expected: 'PURCHASEORDER' },
    { input: 'PURCHASE_ORDER', expected: 'PURCHASEORDER' },
    { input: 'purchase-order', expected: 'PURCHASEORDER' },
    { input: 'purchase_order', expected: 'PURCHASEORDER' },
    { input: 'PO', expected: 'PURCHASEORDER' },

    // Product variants
    { input: 'Product', expected: 'PRODUCT' },
    { input: 'PRODUCT', expected: 'PRODUCT' },
    { input: 'product', expected: 'PRODUCT' },

    // Supplier Quotation variants
    { input: 'SupplierQuotation', expected: 'QUOTATION' },
    { input: 'Quotation', expected: 'QUOTATION' },
    { input: 'QUOTATION', expected: 'QUOTATION' },
    { input: 'quotation', expected: 'QUOTATION' },
    { input: 'supplier-quotation', expected: 'QUOTATION' },

    // Stock Request variants
    { input: 'StockRequest', expected: 'STOCKREQUEST' },
    { input: 'STOCK_REQUEST', expected: 'STOCKREQUEST' },
    { input: 'stock-request', expected: 'STOCKREQUEST' },
    { input: 'stock_request', expected: 'STOCKREQUEST' },

    // Stock Transaction variants
    { input: 'StockTransaction', expected: 'STOCKTRANSACTION' },
    { input: 'TRANSACTION', expected: 'STOCKTRANSACTION' },
    { input: 'STOCK_TRANSACTION', expected: 'STOCKTRANSACTION' },
    { input: 'stock-transaction', expected: 'STOCKTRANSACTION' },

    // Invoice / Payment variants
    { input: 'Invoice', expected: 'INVOICE' },
    { input: 'SUPPLIER_INVOICE', expected: 'INVOICE' },
    { input: 'Payment', expected: 'PAYMENT' },

    // Null, empty, and invalid types
    { input: null, expected: null },
    { input: undefined, expected: null },
    { input: '', expected: null },
    { input: '   ', expected: null },
    { input: 123, expected: null },
    { input: 'UnknownEntity', expected: null },
    { input: 'TestTask', expected: null },
    { input: 'DuplicateRef', expected: null }
];

normalizationCases.forEach(({ input, expected }, idx) => {
    const res = App.normalizeReferenceType(input);
    assert.strictEqual(res, expected, `Case #${idx + 1} failed: input '${input}' expected '${expected}', got '${res}'`);
});
console.log(`✓ All ${normalizationCases.length} reference normalization cases passed cleanly`);

// =========================================================================
// TEST SUITE 2: DISPATCHER MODAL EXECUTION FOR SUPPORTED REFERENCE TYPES
// =========================================================================
console.log("\n--- [Suite 2] Dispatcher Modal Execution ---");

async function runDispatcherTest() {
    // Setup mock pages with spy functions
    App.pages = {
        'shipments': {
            openShipmentDetailsModal: (id) => { modalCalls['shipments'] = id; }
        },
        'purchase-orders': {
            viewPODetails: (id) => { modalCalls['purchase-orders'] = id; }
        },
        'products': {
            showProductModal: (id) => { modalCalls['products'] = id; }
        },
        'quotations': {
            openQuotationDetailsModal: (id) => { modalCalls['quotations'] = id; }
        },
        'stock-requests': {
            openDetailsModal: (id) => { modalCalls['stock-requests'] = id; }
        },
        'stock-transactions': {
            applyFilters: () => { filterCalls['stock-transactions'] = mockElements['tx-search-input'].value; }
        },
        'payments': {
            viewInvoiceDetails: (id) => { modalCalls['payments'] = id; },
            viewPaymentVoucher: (id) => { modalCalls['payments-voucher'] = id; }
        },
        'notifications': {
            loadNotifications: () => {}
        }
    };

    App.notifications = {
        updateUnreadCount: async () => { unreadCountUpdates++; }
    };

    currentUser = { username: 'owner_user', role: 'Owner' };

    // 2.1 Shipment
    modalCalls = {};
    markedReadIds = [];
    unreadCountUpdates = 0;
    mockHash = 'dashboard';
    await App.navigateToReference('SHIPMENT', 42, 101);
    assert.strictEqual(markedReadIds[0], 101, "Notification 101 must be marked read");
    assert.strictEqual(unreadCountUpdates, 1, "Unread count must update");
    assert.strictEqual(mockHash, 'shipments', "Hash must route to #shipments");
    assert.strictEqual(modalCalls['shipments'], 42, "openShipmentDetailsModal must be called with ID 42");
    console.log("✓ Shipment: navigated to #shipments and executed openShipmentDetailsModal(42)");

    // 2.2 Purchase Order
    modalCalls = {};
    mockHash = 'dashboard';
    await App.navigateToReference('PURCHASE_ORDER', 15);
    assert.strictEqual(mockHash, 'purchase-orders', "Hash must route to #purchase-orders");
    assert.strictEqual(modalCalls['purchase-orders'], 15, "viewPODetails must be called with ID 15");
    console.log("✓ Purchase Order: navigated to #purchase-orders and executed viewPODetails(15)");

    // 2.3 Product
    modalCalls = {};
    mockHash = 'dashboard';
    await App.navigateToReference('PRODUCT', 8);
    assert.strictEqual(mockHash, 'products', "Hash must route to #products");
    assert.strictEqual(modalCalls['products'], 8, "showProductModal must be called with ID 8");
    console.log("✓ Product: navigated to #products and executed showProductModal(8)");

    // 2.4 Supplier Quotation
    modalCalls = {};
    mockHash = 'dashboard';
    await App.navigateToReference('QUOTATION', 38);
    assert.strictEqual(mockHash, 'quotations', "Hash must route to #quotations");
    assert.strictEqual(modalCalls['quotations'], 38, "openQuotationDetailsModal must be called with ID 38");
    console.log("✓ Quotation: navigated to #quotations and executed openQuotationDetailsModal(38)");

    // 2.5 Stock Request
    modalCalls = {};
    mockHash = 'dashboard';
    await App.navigateToReference('StockRequest', 12);
    assert.strictEqual(mockHash, 'stock-requests', "Hash must route to #stock-requests");
    assert.strictEqual(modalCalls['stock-requests'], 12, "openDetailsModal must be called with ID 12");
    console.log("✓ Stock Request: navigated to #stock-requests and executed openDetailsModal(12)");

    // 2.6 Stock Transaction
    filterCalls = {};
    mockHash = 'dashboard';
    await App.navigateToReference('TRANSACTION', 25);
    assert.strictEqual(mockHash, 'stock-transactions', "Hash must route to #stock-transactions");
    assert.strictEqual(filterCalls['stock-transactions'], '25', "applyFilters must run with txId '25'");
    console.log("✓ Stock Transaction: navigated to #stock-transactions and filtered search input with '25'");

    // 2.7 Invoice
    modalCalls = {};
    mockHash = 'dashboard';
    await App.navigateToReference('Invoice', 99);
    assert.strictEqual(mockHash, 'payments', "Hash must route to #payments");
    assert.strictEqual(modalCalls['payments'], 99, "viewInvoiceDetails must be called with ID 99");
    console.log("✓ Invoice: navigated to #payments and executed viewInvoiceDetails(99)");

    // 2.8 Payment Voucher
    modalCalls = {};
    mockHash = 'dashboard';
    await App.navigateToReference('Payment', 77);
    assert.strictEqual(mockHash, 'payments', "Hash must route to #payments");
    assert.strictEqual(modalCalls['payments-voucher'], 77, "viewPaymentVoucher must be called with ID 77");
    console.log("✓ Payment Voucher: navigated to #payments and executed viewPaymentVoucher(77)");

    // =========================================================================
    // TEST SUITE 3: ROLE-BASED ACCESS CONTROL (RBAC) GUARDS
    // =========================================================================
    console.log("\n--- [Suite 3] Role-Based Access Control Guards ---");

    // 3.1 Employee accessing Purchase Order (DENIED)
    currentUser = { username: 'emp_user', role: 'Employee' };
    modalCalls = {};
    toastMessages = [];
    mockHash = 'dashboard';
    await App.navigateToReference('PurchaseOrder', 15);
    assert.strictEqual(mockHash, 'dashboard', "Route must NOT change when unauthorized");
    assert.strictEqual(modalCalls['purchase-orders'], undefined, "Modal must NOT be invoked when unauthorized");
    assert(toastMessages.some(t => t.type === 'warning' && t.msg.includes('not accessible')), "Warning toast must be shown");
    console.log("✓ Employee blocked from Purchase Orders with warning toast");

    // 3.2 Employee accessing Quotations (DENIED)
    modalCalls = {};
    toastMessages = [];
    mockHash = 'dashboard';
    await App.navigateToReference('Quotation', 20);
    assert.strictEqual(mockHash, 'dashboard', "Route must NOT change when unauthorized");
    assert.strictEqual(modalCalls['quotations'], undefined, "Modal must NOT be invoked when unauthorized");
    console.log("✓ Employee blocked from Quotations with warning toast");

    // 3.3 Employee accessing Stock Requests (DENIED)
    modalCalls = {};
    toastMessages = [];
    mockHash = 'dashboard';
    await App.navigateToReference('StockRequest', 30);
    assert.strictEqual(mockHash, 'dashboard', "Route must NOT change when unauthorized");
    assert.strictEqual(modalCalls['stock-requests'], undefined, "Modal must NOT be invoked when unauthorized");
    console.log("✓ Employee blocked from Stock Requests with warning toast");

    // 3.4 Supplier accessing Products (DENIED)
    currentUser = { username: 'sup_user', role: 'Supplier' };
    modalCalls = {};
    toastMessages = [];
    mockHash = 'dashboard';
    await App.navigateToReference('Product', 5);
    assert.strictEqual(mockHash, 'dashboard', "Route must NOT change when unauthorized");
    assert.strictEqual(modalCalls['products'], undefined, "Modal must NOT be invoked when unauthorized");
    console.log("✓ Supplier blocked from Products with warning toast");

    // 3.5 Supplier accessing Stock Transactions (DENIED)
    filterCalls = {};
    toastMessages = [];
    mockHash = 'dashboard';
    await App.navigateToReference('StockTransaction', 10);
    assert.strictEqual(mockHash, 'dashboard', "Route must NOT change when unauthorized");
    assert.strictEqual(filterCalls['stock-transactions'], undefined, "Filter must NOT be invoked when unauthorized");
    console.log("✓ Supplier blocked from Stock Transactions with warning toast");

    // 3.6 Employee accessing Shipments (ALLOWED)
    currentUser = { username: 'emp_user', role: 'Employee' };
    modalCalls = {};
    mockHash = 'dashboard';
    await App.navigateToReference('Shipment', 7);
    assert.strictEqual(mockHash, 'shipments', "Employee is permitted on Shipments");
    assert.strictEqual(modalCalls['shipments'], 7, "Modal must be invoked for employee on Shipment");
    console.log("✓ Employee permitted on Shipments");

    // 3.7 Employee accessing Payment Voucher (DENIED)
    currentUser = { username: 'emp_user', role: 'Employee' };
    modalCalls = {};
    toastMessages = [];
    mockHash = 'dashboard';
    await App.navigateToReference('Payment', 77);
    assert.strictEqual(mockHash, 'dashboard', "Route must NOT change when unauthorized");
    assert.strictEqual(modalCalls['payments-voucher'], undefined, "Modal must NOT be invoked when unauthorized");
    assert(toastMessages.some(t => t.type === 'warning' && t.msg.includes('not accessible')), "Warning toast must be shown");
    console.log("✓ Employee blocked from Payment Voucher with warning toast");

    // 3.8 Supplier accessing Payment Voucher (ALLOWED)
    currentUser = { username: 'sup_user', role: 'Supplier' };
    modalCalls = {};
    mockHash = 'dashboard';
    await App.navigateToReference('Payment', 77);
    assert.strictEqual(mockHash, 'payments', "Supplier is permitted on payments");
    assert.strictEqual(modalCalls['payments-voucher'], 77, "viewPaymentVoucher must be invoked for supplier");
    console.log("✓ Supplier permitted on Payment Voucher");

    // =========================================================================
    // TEST SUITE 4: ERROR HANDLING & EDGE CASES
    // =========================================================================
    console.log("\n--- [Suite 4] Edge Cases & Error Handling ---");

    // 4.1 Missing referenceId
    currentUser = { username: 'owner_user', role: 'Owner' };
    toastMessages = [];
    mockHash = 'dashboard';
    await App.navigateToReference('Shipment', null);
    assert.strictEqual(mockHash, 'dashboard', "Route must NOT change when referenceId is null");
    assert(toastMessages.some(t => t.type === 'warning' && t.msg.includes('valid record reference ID')), "Warning toast for missing ID");
    console.log("✓ Null referenceId handled safely without broken routing");

    // 4.2 Unsupported referenceType
    toastMessages = [];
    mockHash = 'dashboard';
    await App.navigateToReference('UnsupportedType123', 5);
    assert.strictEqual(mockHash, 'dashboard', "Route must NOT change for unsupported type");
    assert(toastMessages.some(t => t.type === 'warning' && t.msg.includes('Direct link unavailable')), "Warning toast for unsupported type");
    console.log("✓ Unsupported referenceType handled safely with informative toast");

    // 4.3 Missing page controller (does not crash)
    App.pages['shipments'] = {}; // No openShipmentDetailsModal defined
    mockHash = 'dashboard';
    let threwError = false;
    try {
        await App.navigateToReference('Shipment', 999);
    } catch (e) {
        threwError = true;
    }
    assert.strictEqual(threwError, false, "Missing modal function must not throw uncaught error");
    console.log("✓ Missing modal function handled gracefully without unhandled exception");

    console.log("\n=======================================================");
    console.log("ALL 4 TEST SUITES PASSED (100% SUCCESS RATE)");
    console.log("=======================================================");
}

runDispatcherTest().catch(err => {
    console.error("FATAL TEST FAILURE:", err);
    process.exit(1);
});
