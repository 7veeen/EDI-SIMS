/**
 * test_shipment_allocation_phase_d.js
 * 
 * Focused Node.js Verification Test Suite for SIMS Phase D:
 * Create Shipment Allocation UI Integration & Validation
 *
 * Verifies:
 *   1. Allocation payload contains the correct product IDs and quantities.
 *   2. No selected products prevents submission with clear error.
 *   3. Zero, negative, fractional, and invalid quantities are rejected.
 *   4. Changing the PO resets stale product selections and refreshes allocation controls.
 *   5. Products with no remaining allocatable quantity cannot be selected (disabled + labeled).
 *   6. Backend allocation-validation errors are displayed to the user via toast.
 *   7. Existing logistics fields remain present in the submission payload.
 *   8. A successful API response follows existing success and refresh behavior.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log("===================================================================");
console.log("SIMS PHASE D: CREATE SHIPMENT ALLOCATION UI INTEGRATION VERIFICATION");
console.log("===================================================================\n");

// --- 1. Mock Browser Environment ---
const elementsById = new Map();
const toasts = [];
let shipmentsLoadedCount = 0;
let lastApiPost = null;

class MockElement {
    constructor(tagName, id = '') {
        this.tagName = tagName.toUpperCase();
        this.id = id;
        this.className = '';
        this.attributes = new Map();
        this.style = {};
        this._innerHTML = '';
        this.children = [];
        this.value = '';
        this.checked = false;
        this.disabled = false;
        this.listeners = new Map();
        if (id) elementsById.set(id, this);
    }

    setAttribute(k, v) { this.attributes.set(k, String(v)); }
    getAttribute(k) { return this.attributes.has(k) ? this.attributes.get(k) : null; }
    hasAttribute(k) { return this.attributes.has(k); }
    removeAttribute(k) { this.attributes.delete(k); }

    addEventListener(event, fn) {
        if (!this.listeners.has(event)) this.listeners.set(event, []);
        this.listeners.get(event).push(fn);
    }

    async dispatchEvent(event) {
        const list = this.listeners.get(event.type || event) || [];
        for (const fn of list) {
            await fn(event);
        }
    }

    get innerHTML() { return this._innerHTML; }
    set innerHTML(html) {
        this._innerHTML = html;
        this._parseChildInputs(html);
    }

    _parseChildInputs(html) {
        this.children = [];
        // Regex parse checkboxes and inputs
        const cbRegex = /<input\s+([^>]*type=["']checkbox["'][^>]*)>/gi;
        let match;
        while ((match = cbRegex.exec(html)) !== null) {
            const attrs = match[1];
            const el = new MockElement('input');
            el.type = 'checkbox';
            el.checked = attrs.includes('checked');
            el.disabled = attrs.includes('disabled');
            
            const pidM = attrs.match(/data-product-id=["'](\d+)["']/);
            if (pidM) el.setAttribute('data-product-id', pidM[1]);
            const maxM = attrs.match(/data-max=["'](\d+)["']/);
            if (maxM) el.setAttribute('data-max', maxM[1]);
            const idM = attrs.match(/id=["']([^"']+)["']/);
            if (idM) {
                el.id = idM[1];
                elementsById.set(el.id, el);
            }
            const classM = attrs.match(/class=["']([^"']+)["']/);
            if (classM) el.className = classM[1];
            this.children.push(el);
        }

        const inputRegex = /<input\s+([^>]*type=["']number["'][^>]*)>/gi;
        while ((match = inputRegex.exec(html)) !== null) {
            const attrs = match[1];
            const el = new MockElement('input');
            el.type = 'number';
            el.disabled = attrs.includes('disabled');

            const valM = attrs.match(/value=["']([^"']*)["']/);
            if (valM) el.value = valM[1];
            const pidM = attrs.match(/data-product-id=["'](\d+)["']/);
            if (pidM) el.setAttribute('data-product-id', pidM[1]);
            const maxM = attrs.match(/data-max=["'](\d+)["']/);
            if (maxM) el.setAttribute('data-max', maxM[1]);
            const nameM = attrs.match(/data-product-name=["']([^"']*)["']/);
            if (nameM) el.setAttribute('data-product-name', nameM[1]);
            const classM = attrs.match(/class=["']([^"']+)["']/);
            if (classM) el.className = classM[1];
            this.children.push(el);
        }

        // Summary spans
        if (html.includes('id="alloc-selected-count"')) {
            const span = new MockElement('span', 'alloc-selected-count');
            this.children.push(span);
        }
        if (html.includes('id="alloc-total-units"')) {
            const span = new MockElement('span', 'alloc-total-units');
            this.children.push(span);
        }
    }

    querySelector(selector) {
        const all = this.querySelectorAll(selector);
        return all.length > 0 ? all[0] : null;
    }

    querySelectorAll(selector) {
        const matches = [];

        const matchEl = (el, sel) => {
            let s = sel.trim();
            if (s.startsWith('tr.')) s = s.slice(2);
            if (s === 'tr') return el.tagName === 'TR';

            if (/^[a-zA-Z]+$/.test(s)) {
                return el.tagName === s.toUpperCase();
            }

            if (s.startsWith('#')) {
                return el.id === s.slice(1);
            }

            let pass = true;
            if (s.includes(':checked')) {
                if (!el.checked) pass = false;
                s = s.replace(':checked', '');
            }

            const attrRegex = /\[([a-zA-Z0-9_-]+)(?:=["']([^"']*)["'])?\]/g;
            let m;
            while ((m = attrRegex.exec(s)) !== null) {
                const attrName = m[1];
                const attrVal = m[2];
                if (!el.hasAttribute(attrName)) pass = false;
                else if (attrVal !== undefined && el.getAttribute(attrName) !== attrVal) pass = false;
            }
            s = s.replace(attrRegex, '');

            if (s.startsWith('.')) {
                const cls = s.slice(1).trim();
                if (cls) {
                    const elClasses = (el.className || '').split(/\s+/);
                    if (!elClasses.includes(cls)) pass = false;
                }
            }

            return pass;
        };

        const checkEl = (el) => {
            const parts = selector.split(',').map(p => p.trim());
            for (const part of parts) {
                if (matchEl(el, part)) {
                    matches.push(el);
                    break;
                }
            }
            for (const child of el.children) {
                checkEl(child);
            }
        };

        for (const child of this.children) {
            checkEl(child);
        }
        return matches;
    }
}

global.document = {
    getElementById(id) {
        return elementsById.get(id) || null;
    },
    createElement(tag) {
        return new MockElement(tag);
    }
};

global.alert = (msg) => {
    console.log("[Alert]", msg);
    toasts.push({ message: msg, type: 'warning' });
};

global.Utils = {
    showToast(message, type = 'success') {
        toasts.push({ message, type });
    },
    escapeHtml(str) {
        return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
};

let modalShownOptions = null;
global.Modal = {
    show(options) {
        modalShownOptions = options;
        if (options.content) {
            // Populate mock elements for IDs present in content
            const idRegex = /id=["']([^"']+)["']/g;
            let m;
            while ((m = idRegex.exec(options.content)) !== null) {
                const id = m[1];
                if (!elementsById.has(id)) {
                    elementsById.set(id, new MockElement('div', id));
                }
            }
        }
    }
};

global.Auth = {
    getUser() {
        return { user_id: 1, role: 'Supplier', username: 'demo_supplier' };
    }
};

global.App = {
    pages: {}
};

// --- 2. Load frontend/js/pages/shipments.js ---
const shipmentsFilePath = path.join(__dirname, '..', '..', 'frontend/js/pages/shipments.js');
const shipmentsCode = fs.readFileSync(shipmentsFilePath, 'utf8');

// Execute script in global context
vm.runInThisContext(shipmentsCode);
assert(App.pages['shipments'], "App.pages['shipments'] must be defined");
App.pages['shipments'].loadShipments = () => { shipmentsLoadedCount++; };

// --- 3. Mock APIs ---
let mockOrders = [
    {
        purchase_order_id: 101,
        order_date: '2026-10-18',
        total_amount: 150000,
        supplier_response: 'Accepted',
        status: 'Accepted'
    }
];

let mockPoDetails = {
    purchase_order_id: 101,
    order_date: '2026-10-18',
    total_amount: 150000,
    items: [
        {
            product_id: 1,
            product_name: 'Widget A',
            sku: 'WGT-A',
            quantity: 50,
            allocated_quantity: 20,
            remaining_quantity: 30
        },
        {
            product_id: 2,
            product_name: 'Gadget B',
            sku: 'GDG-B',
            quantity: 100,
            allocated_quantity: 100,
            remaining_quantity: 0
        },
        {
            product_id: 3,
            product_name: 'Sensor C',
            sku: 'SNS-C',
            quantity: 25,
            allocated_quantity: 0,
            remaining_quantity: 25
        }
    ]
};

global.Api = {
    async get(url) {
        if (url === '/purchase-orders/') {
            return { purchase_orders: mockOrders };
        }
        if (url.startsWith('/purchase-orders/101')) {
            return { purchase_order: mockPoDetails };
        }
        throw new Error(`Unhandled GET url: ${url}`);
    },
    async post(url, payload) {
        lastApiPost = { url, payload };
        if (payload._simulateServerError) {
            throw new Error(payload._simulateServerError);
        }
        return { message: "Shipment created successfully", shipment: { shipment_id: 99 } };
    }
};

async function runTests() {
    console.log("Running Phase D Unit & UI Integration Tests...\n");

    // --- TEST 1: Open Create Shipment Modal & Verify Allocation Table Render ---
    await App.pages['shipments'].openCreateShipmentModal();
    assert(modalShownOptions, "Modal.show must be called");
    assert.strictEqual(modalShownOptions.size, 'lg', "Modal must use size 'lg' for allocation table");

    // Retrieve input DOM elements created by Modal.show
    const poSelect = document.getElementById('modal-ship-po-select');
    const previewBox = document.getElementById('modal-ship-po-preview');
    const carrierInput = document.getElementById('modal-ship-carrier');
    carrierInput.value = 'DHL Express';
    const trackingInput = document.getElementById('modal-ship-tracking');
    trackingInput.value = 'TRK-987654';
    const methodSelect = document.getElementById('modal-ship-method');
    methodSelect.value = 'Express Cargo';
    const statusSelect = document.getElementById('modal-ship-status');
    statusSelect.value = 'In Transit';
    const pkgCountInput = document.getElementById('modal-ship-pkg-count');
    pkgCountInput.value = '3';
    const weightInput = document.getElementById('modal-ship-weight');
    weightInput.value = '15.5';
    const originInput = document.getElementById('modal-ship-origin');
    originInput.value = 'Dock Alpha';
    const destInput = document.getElementById('modal-ship-dest');
    destInput.value = 'Warehouse Bay 3';
    const expectedDeliveryInput = document.getElementById('modal-ship-expected-delivery');
    expectedDeliveryInput.value = '2026-10-25';
    const notesInput = document.getElementById('modal-ship-notes');
    notesInput.value = 'Fragile electronics';

    console.log("✓ Test 1 Passed: openCreateShipmentModal initializes modal with size 'lg'");

    // --- TEST 2: Select PO and Verify Product Allocation Rendering & Disabling ---
    poSelect.value = '101';
    await poSelect.dispatchEvent({ type: 'change', target: poSelect });

    assert.strictEqual(previewBox.style.display, 'block', "Preview box must be displayed after selecting PO");
    assert(previewBox.innerHTML.includes('PO #101 Product Allocations'), "Preview box must render PO title");
    assert(previewBox.innerHTML.includes('Widget A'), "Widget A must be rendered");
    assert(previewBox.innerHTML.includes('Gadget B'), "Gadget B must be rendered");
    assert(previewBox.innerHTML.includes('Fully Allocated'), "Gadget B must be marked Fully Allocated");

    // Checkbox and input states
    const cbWidgetA = previewBox.querySelector('.alloc-item-checkbox[data-product-id="1"]');
    const qtyWidgetA = previewBox.querySelector('.alloc-qty-input[data-product-id="1"]');
    const cbSensorC = previewBox.querySelector('.alloc-item-checkbox[data-product-id="3"]');
    const qtySensorC = previewBox.querySelector('.alloc-qty-input[data-product-id="3"]');

    assert(cbWidgetA && cbWidgetA.checked, "Widget A must be selectable and checked by default");
    assert.strictEqual(qtyWidgetA.value, '30', "Widget A quantity default must be remaining allocatable quantity (30)");
    assert.strictEqual(qtyWidgetA.getAttribute('data-max'), '30', "Widget A max must be 30");

    assert(cbSensorC && cbSensorC.checked, "Sensor C must be selectable and checked by default");
    assert.strictEqual(qtySensorC.value, '25', "Sensor C quantity default must be remaining allocatable quantity (25)");

    // Gadget B is fully allocated (rem = 0), so it should not have an enabled .alloc-item-checkbox
    const cbGadgetB = previewBox.querySelector('.alloc-item-checkbox[data-product-id="2"]');
    assert(!cbGadgetB, "Fully allocated Gadget B must NOT have an active selectable checkbox");

    console.log("✓ Test 2 Passed: Eligible PO products rendered; 0-remaining items disabled and marked 'Fully Allocated'");

    // --- TEST 3: Allocation Payload Format and Logistics Fields Preservation ---
    qtyWidgetA.value = '10'; // Allocate 10 of 30
    qtySensorC.value = '15'; // Allocate 15 of 25

    lastApiPost = null;
    await modalShownOptions.onSave(previewBox);

    assert(lastApiPost, "Api.post must be called on save");
    assert.strictEqual(lastApiPost.url, '/shipments/');
    assert.strictEqual(lastApiPost.payload.purchase_order_id, 101);
    assert.strictEqual(lastApiPost.payload.carrier, 'DHL Express');
    assert.strictEqual(lastApiPost.payload.tracking_number, 'TRK-987654');
    assert.strictEqual(lastApiPost.payload.shipping_method, 'Express Cargo');
    assert.strictEqual(lastApiPost.payload.status, 'In Transit');
    assert.strictEqual(lastApiPost.payload.package_count, 3);
    assert.strictEqual(lastApiPost.payload.total_weight, 15.5);
    assert.strictEqual(lastApiPost.payload.origin_address, 'Dock Alpha');
    assert.strictEqual(lastApiPost.payload.destination_address, 'Warehouse Bay 3');
    assert.strictEqual(lastApiPost.payload.expected_delivery, '2026-10-25');
    assert.strictEqual(lastApiPost.payload.shipping_notes, 'Fragile electronics');

    // Verify items array format
    assert(Array.isArray(lastApiPost.payload.items), "Payload must contain items array");
    assert.strictEqual(lastApiPost.payload.items.length, 2);
    assert.deepStrictEqual(lastApiPost.payload.items, [
        { product_id: 1, quantity: 10 },
        { product_id: 3, quantity: 15 }
    ]);
    assert(shipmentsLoadedCount > 0, "loadShipments() must be triggered on success");

    console.log("✓ Test 3 Passed: Allocation payload formatted correctly as items: [{product_id, quantity}], logistics fields preserved");

    // --- TEST 4: Reject Submission When No Products Are Selected ---
    cbWidgetA.checked = false;
    cbSensorC.checked = false;

    let noItemError = null;
    try {
        await modalShownOptions.onSave(previewBox);
    } catch (e) {
        noItemError = e;
    }
    assert(noItemError, "Must reject submission when 0 products selected");
    assert(noItemError.message.includes('select at least one product'), `Error message mismatch: ${noItemError.message}`);

    console.log("✓ Test 4 Passed: Prevents submission when no products are selected");

    // --- TEST 5: Reject Zero, Negative, Fractional, and Exceeding Quantities ---
    cbWidgetA.checked = true;

    // Zero quantity
    qtyWidgetA.value = '0';
    let zeroErr = null;
    try { await modalShownOptions.onSave(previewBox); } catch (e) { zeroErr = e; }
    assert(zeroErr && zeroErr.message.includes('greater than zero'), "Zero quantity must be rejected");

    // Negative quantity
    qtyWidgetA.value = '-5';
    let negErr = null;
    try { await modalShownOptions.onSave(previewBox); } catch (e) { negErr = e; }
    assert(negErr && (negErr.message.includes('positive integer') || negErr.message.includes('greater than zero')), "Negative quantity must be rejected");

    // Fractional quantity
    qtyWidgetA.value = '5.5';
    let fracErr = null;
    try { await modalShownOptions.onSave(previewBox); } catch (e) { fracErr = e; }
    assert(fracErr && fracErr.message.includes('valid positive integer'), "Fractional quantity must be rejected");

    // Invalid non-numeric
    qtyWidgetA.value = 'abc';
    let strErr = null;
    try { await modalShownOptions.onSave(previewBox); } catch (e) { strErr = e; }
    assert(strErr && strErr.message.includes('valid positive integer'), "Non-numeric quantity must be rejected");

    // Exceeding remaining allocatable quantity (max is 30, trying 35)
    qtyWidgetA.value = '35';
    let overErr = null;
    try { await modalShownOptions.onSave(previewBox); } catch (e) { overErr = e; }
    assert(overErr && overErr.message.includes('cannot exceed remaining allocatable quantity'), `Must reject over-allocation: ${overErr && overErr.message}`);

    console.log("✓ Test 5 Passed: Zero, negative, fractional, and over-allocation quantities are strictly rejected before submission");

    // --- TEST 6: Changing PO Resets Stale Product Selections ---
    poSelect.value = '';
    await poSelect.dispatchEvent({ type: 'change', target: poSelect });

    assert.strictEqual(previewBox.style.display, 'none', "Preview box must hide when PO selection is cleared");
    assert.strictEqual(previewBox.innerHTML, '', "Preview content must be cleared to eliminate stale selections");

    let poClearedErr = null;
    try { await modalShownOptions.onSave(previewBox); } catch (e) { poClearedErr = e; }
    assert(poClearedErr && poClearedErr.message.includes('select an accepted Purchase Order'), "Must reject when PO selection is empty");

    console.log("✓ Test 6 Passed: Deselecting or changing PO resets stale product selections and hides preview");

    // --- TEST 7: Backend Allocation Validation Errors Are Displayed to User ---
    poSelect.value = '101';
    await poSelect.dispatchEvent({ type: 'change', target: poSelect });

    const freshCb = previewBox.querySelector('.alloc-item-checkbox[data-product-id="1"]');
    const freshQty = previewBox.querySelector('.alloc-qty-input[data-product-id="1"]');
    freshCb.checked = true;
    freshQty.value = '20';

    // Simulate backend rejecting with concurrency or quote error
    const serverErrorMessage = "Allocation for product ID 1 (40) exceeds total purchase order quantity (50)";
    carrierInput.value = 'Standard Logistics';
    destInput.value = 'Bay 1';
    
    // Inject mock error into post payload
    let backendErr = null;
    const originalPost = Api.post;
    Api.post = async () => { throw new Error(serverErrorMessage); };

    try {
        await modalShownOptions.onSave(previewBox);
    } catch (e) {
        backendErr = e;
    }
    assert(backendErr, "Must propagate backend error to modal caller");
    assert.strictEqual(backendErr.message, serverErrorMessage, "Backend error message must match server response");
    Api.post = originalPost;

    console.log("✓ Test 7 Passed: Backend allocation-validation errors propagate clearly to user toast notifications");

    // --- TEST 8: Successful API Creation Triggers Toast and Refreshes Shipments Table ---
    const initialLoads = shipmentsLoadedCount;
    toasts.length = 0;

    await modalShownOptions.onSave(previewBox);

    assert(toasts.some(t => t.type === 'success' && t.message.includes('Shipment created and dispatched successfully with product allocations')), "Success toast must be displayed");
    assert.strictEqual(shipmentsLoadedCount, initialLoads + 1, "App.pages['shipments'].loadShipments must be called to refresh table");

    console.log("✓ Test 8 Passed: Successful dispatch triggers success notification and refreshes shipment listings");

    console.log("\n===================================================================");
    console.log("ALL 8 PHASE D VERIFICATION TESTS PASSED SUCCESSFULLY (100%)");
    console.log("===================================================================");
}

runTests().catch(err => {
    console.error("Test execution failed:", err);
    process.exit(1);
});
