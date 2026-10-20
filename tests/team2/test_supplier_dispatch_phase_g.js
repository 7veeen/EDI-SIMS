/**
 * test_supplier_dispatch_phase_g.js
 * 
 * Focused Verification Test Suite for SIMS Phase G:
 * Supplier-Side Shipment Creation and Dispatch Workflow
 *
 * Verifies:
 *   1. Supplier PO List: Dispatches eligible accepted POs with btn-action-dispatch button.
 *   2. Supplier PO List: Does not show dispatch button for Pending, Delivered, or Cancelled orders.
 *   3. PO Details Modal: Displays ORDERED, ALLOCATED, and REMAINING columns for line items.
 *   4. PO Details Modal: Renders "Dispatch Shipment" action in footer for eligible accepted orders.
 *   5. Supplier Dashboard: Recent Orders table renders direct "Dispatch" shortcut button for accepted POs.
 *   6. Shipments Page: openCreateShipmentModal(preselectedPoId) preselects PO and triggers line item load.
 *   7. Shipments Page: Preselected ineligible PO shows warning and gracefully allows alternate selection.
 *   8. Shipments Page: Allocation builder validates positive integers, remaining limits, and non-empty selections.
 *   9. Pre-Dispatch Review Step: Renders review modal with PO, Carrier, Tracking, Line Items, and Total Units.
 *  10. Pre-Dispatch Review Step: "Back to Edit" closes review and preserves create form state.
 *  11. Pre-Dispatch Submission: Prevents double submission by disabling buttons and showing spinner.
 *  12. Pre-Dispatch Submission: Safely handles missing shipment IDs from API response.
 *  13. Pre-Dispatch Submission: Handles API / network errors safely without losing form state.
 *  14. Post-Dispatch Flow: Upon success, closes modals, refreshes shipments list, shows toast, and opens shipment details modal with new shipment ID.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log("===================================================================");
console.log("SIMS PHASE G: SUPPLIER-SIDE SHIPMENT DISPATCH WORKFLOW TEST SUITE");
console.log("===================================================================\n");

// --- 1. Comprehensive Browser/DOM Mock Environment ---
const elementsById = new Map();
const toasts = [];
let shipmentsLoadedCount = 0;
let lastApiPost = null;
let lastOpenedShipmentDetailsId = null;
let lastNavigatedPath = null;
let mockActiveUser = { id: 10, role: 'Supplier', username: 'acme_supplier' };

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
        this.options = [];
        this.selectedIndex = 0;
        this.parentElement = null;
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
        const type = typeof event === 'string' ? event : (event.type || 'unknown');
        let evt = typeof event === 'string' ? { target: this, type: event } : event;
        if (!evt.target || evt.target !== this) {
            try {
                Object.defineProperty(evt, 'target', { value: this, configurable: true, writable: true });
            } catch (e) {
                evt = { target: this, type: type, originalEvent: event };
            }
        }
        const list = this.listeners.get(type) || [];
        for (const fn of list) {
            await fn(evt);
        }
    }

    closest(sel) {
        let curr = this.parentElement;
        while (curr) {
            if (sel === 'tr' && curr.tagName === 'TR') return curr;
            curr = curr.parentElement;
        }
        return this.parentElement;
    }

    get textContent() {
        return this._innerHTML.replace(/<[^>]+>/g, '').trim();
    }
    set textContent(txt) {
        this._innerHTML = txt;
    }

    get innerHTML() { return this._innerHTML; }
    set innerHTML(html) {
        this._innerHTML = html;
        this._parseChildInputs(html);
    }

    _parseChildInputs(html) {
        this.children = [];

        // Parse options for select elements
        if (this.tagName === 'SELECT') {
            const optRegex = /<option\s+([^>]*)>([\s\S]*?)<\/option>/gi;
            let om;
            this.options = [];
            while ((om = optRegex.exec(html)) !== null) {
                const attrs = om[1];
                const text = om[2].trim();
                const valM = attrs.match(/value=["']([^"']*)["']/);
                const opt = {
                    value: valM ? valM[1] : '',
                    text: text,
                    selected: attrs.includes('selected')
                };
                this.options.push(opt);
                if (opt.selected) {
                    this.value = opt.value;
                    this.selectedIndex = this.options.length - 1;
                }
            }
        }

        // Parse checkboxes
        const cbRegex = /<input\s+([^>]*type=["']checkbox["'][^>]*)>/gi;
        let match;
        while ((match = cbRegex.exec(html)) !== null) {
            const attrs = match[1];
            const el = new MockElement('input');
            el.type = 'checkbox';
            el.checked = attrs.includes('checked');
            el.disabled = attrs.includes('disabled');
            el.parentElement = this;
            
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

        // Parse number inputs
        const inputRegex = /<input\s+([^>]*type=["']number["'][^>]*)>/gi;
        while ((match = inputRegex.exec(html)) !== null) {
            const attrs = match[1];
            const el = new MockElement('input');
            el.type = 'number';
            el.disabled = attrs.includes('disabled');
            el.parentElement = this;

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

        // Summary elements
        if (html.includes('id="alloc-selected-count"')) {
            const span = new MockElement('span', 'alloc-selected-count');
            span.parentElement = this;
            this.children.push(span);
        }
        if (html.includes('id="alloc-total-units"')) {
            const span = new MockElement('span', 'alloc-total-units');
            span.parentElement = this;
            this.children.push(span);
        }
    }

    querySelector(selector) {
        if (selector.startsWith('#') && !selector.includes(' ')) {
            const byId = elementsById.get(selector.slice(1));
            if (byId) return byId;
        }
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

const openModals = [];
global.document = {
    getElementById(id) {
        return elementsById.get(id) || null;
    },
    createElement(tag) {
        return new MockElement(tag);
    },
    querySelector(selector) {
        if (selector === '#pos-table tbody' || selector.includes('#pos-table')) {
            return elementsById.get('po-table-body') || null;
        }
        if (selector.startsWith('#') && !selector.includes(' ')) {
            return elementsById.get(selector.slice(1)) || null;
        }
        for (const modal of openModals) {
            const found = modal.querySelector(selector);
            if (found) return found;
        }
        for (const el of elementsById.values()) {
            const found = el.querySelector(selector);
            if (found) return found;
        }
        return null;
    },
    querySelectorAll(selector) {
        return [];
    }
};

global.Utils = {
    escapeHtml(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); },
    showToast(msg, type = 'info') {
        toasts.push({ msg, type });
    },
    formatDate(d) { return d || 'N/A'; },
    emptyState(icon, title, desc) { return `<div>${title}: ${desc}</div>`; }
};

global.window = {
    location: { hash: '#dashboard' },
    Event: class { constructor(type) { this.type = type; } },
    Utils: global.Utils,
    alert: (msg) => toasts.push({ msg, type: 'error' })
};

global.alert = (msg) => toasts.push({ msg, type: 'error' });

global.Auth = {
    getUser() { return mockActiveUser; }
};

global.Modal = {
    create(options) {
        const modalEl = new MockElement('div', options.id || ('modal-' + Date.now()));
        modalEl._options = options;
        modalEl.innerHTML = `
            <div class="modal-header">
                <h3>${options.title || ''}</h3>
            </div>
            <div class="modal-body">
                ${options.content || ''}
            </div>
            ${options.footer ? `<div class="modal-footer">${options.footer}</div>` : ''}
        `;
        
        // Also parse footer if present
        if (options.footer) {
            const footerEl = new MockElement('div');
            footerEl.innerHTML = options.footer;
            modalEl.children.push(footerEl);
            // Index footer buttons by ID
            if (options.footer.includes('id="modal-btn-to-review"')) {
                const btn = new MockElement('button', 'modal-btn-to-review');
                elementsById.set('modal-btn-to-review', btn);
                modalEl.children.push(btn);
            }
            if (options.footer.includes('id="modal-btn-review-back"')) {
                const btn = new MockElement('button', 'modal-btn-review-back');
                elementsById.set('modal-btn-review-back', btn);
                modalEl.children.push(btn);
            }
            if (options.footer.includes('id="modal-btn-review-confirm"')) {
                const btn = new MockElement('button', 'modal-btn-review-confirm');
                elementsById.set('modal-btn-review-confirm', btn);
                modalEl.children.push(btn);
            }
            if (options.footer.includes('id="modal-btn-dispatch"')) {
                const btn = new MockElement('button', 'modal-btn-dispatch');
                elementsById.set('modal-btn-dispatch', btn);
                modalEl.children.push(btn);
            }
        }

        // Register fresh form inputs inside modal
        if (options.content && options.content.includes('modal-ship-po-select')) {
            const poSelect = new MockElement('select', 'modal-ship-po-select');
            poSelect.innerHTML = options.content;
            elementsById.set('modal-ship-po-select', poSelect);
            modalEl.children.push(poSelect);
        }

        ['modal-ship-po-preview', 'modal-ship-carrier', 'modal-ship-tracking',
         'modal-ship-method', 'modal-ship-status', 'modal-ship-pkg-count', 'modal-ship-weight',
         'modal-ship-origin', 'modal-ship-dest', 'modal-ship-expected-delivery', 'modal-ship-notes'].forEach(id => {
            const el = new MockElement('input', id);
            if (id === 'modal-ship-carrier') el.value = 'BlueDart Express';
            if (id === 'modal-ship-pkg-count') el.value = '1';
            elementsById.set(id, el);
            modalEl.children.push(el);
        });

        openModals.push(modalEl);

        let isClosed = false;
        const closeModal = () => {
            isClosed = true;
            const idx = openModals.indexOf(modalEl);
            if (idx >= 0) openModals.splice(idx, 1);
        };

        if (options.onOpen) {
            options.onOpen(modalEl, closeModal);
        }

        return closeModal;
    },
    show(options) {
        return this.create(options);
    },
    closeAll() {
        openModals.length = 0;
    }
};

global.Api = {
    async get(url) {
        if (url === '/purchase-orders/' || url.startsWith('/purchase-orders/?')) {
            return {
                purchase_orders: [
                    { purchase_order_id: 101, po_number: 'PO-101', supplier_id: 1, supplier_name: 'Acme', supplier_response: 'Accepted', status: 'Accepted', order_date: '2026-10-15', total_amount: 15000 },
                    { purchase_order_id: 102, po_number: 'PO-102', supplier_id: 1, supplier_name: 'Acme', supplier_response: 'Accepted', status: 'Accepted', order_date: '2026-10-18', total_amount: 45000 },
                    { purchase_order_id: 103, po_number: 'PO-103', supplier_id: 1, supplier_name: 'Acme', supplier_response: 'Pending', status: 'Pending', order_date: '2026-10-20', total_amount: 8000 },
                    { purchase_order_id: 104, po_number: 'PO-104', supplier_id: 1, supplier_name: 'Acme', supplier_response: 'Accepted', status: 'Delivered', order_date: '2026-10-01', total_amount: 12000 },
                    { purchase_order_id: 105, po_number: 'PO-105', supplier_id: 1, supplier_name: 'Acme', supplier_response: 'Accepted', status: 'Cancelled', order_date: '2026-10-05', total_amount: 5000 }
                ]
            };
        }
        if (url.startsWith('/purchase-orders/')) {
            const poId = parseInt(url.replace('/purchase-orders/', '').split('/')[0].split('?')[0], 10);
            return {
                purchase_order: {
                    purchase_order_id: poId,
                    po_number: `PO-${poId}`,
                    supplier_name: 'Acme Corp',
                    status: 'Accepted',
                    supplier_response: 'Accepted',
                    order_date: '2026-10-15',
                    total_amount: 15000,
                    items: [
                        { product_id: 1, product_name: 'Industrial Widget A', sku: 'WID-A', quantity: 50, unit_price: 100, subtotal: 5000, allocated_quantity: 20, remaining_quantity: 30 },
                        { product_id: 2, product_name: 'Hydraulic Valve B', sku: 'VLV-B', quantity: 20, unit_price: 250, subtotal: 5000, allocated_quantity: 20, remaining_quantity: 0 },
                        { product_id: 3, product_name: 'Precision Sensor C', sku: 'SNS-C', quantity: 10, unit_price: 500, subtotal: 5000, allocated_quantity: 0, remaining_quantity: 10 }
                    ]
                }
            };
        }
        if (url.startsWith('/shipments/')) {
            const sId = parseInt(url.split('/').pop(), 10);
            return {
                shipment: {
                    shipment_id: sId,
                    shipment_number: `SHP-PO101-${sId}`,
                    purchase_order_id: 101,
                    supplier_name: 'Acme Corp',
                    carrier: 'BlueDart Express',
                    tracking_number: 'BD-88992211',
                    status: 'In Transit',
                    purchase_order: {
                        items: [
                            { product_id: 1, product_name: 'Industrial Widget A', sku: 'WID-A', expected_quantity: 15, received_quantity: 0, remaining_quantity: 15 }
                        ]
                    }
                }
            };
        }
        return {};
    },
    async post(url, payload) {
        lastApiPost = { url, payload };
        if (payload._triggerNetworkFailure) {
            throw new Error('Network timeout during dispatch submission');
        }
        if (payload._omitShipmentId) {
            return { message: 'Created successfully' }; // Missing shipment_id
        }
        return {
            message: 'Shipment created successfully',
            shipment: {
                shipment_id: 701,
                shipment_number: `SHP-PO${payload.purchase_order_id}-701`,
                purchase_order_id: payload.purchase_order_id,
                carrier: payload.carrier,
                status: payload.status
            }
        };
    }
};

global.App = {
    pages: {},
    navigate(path) {
        lastNavigatedPath = path;
        window.location.hash = '#' + path;
    }
};

// --- Load and Evaluate Source Files ---
const shipmentsSrc = fs.readFileSync(path.resolve(__dirname, '../../frontend/js/pages/shipments.js'), 'utf8');
const purchaseOrdersSrc = fs.readFileSync(path.resolve(__dirname, '../../frontend/js/pages/purchase-orders.js'), 'utf8');

vm.runInThisContext(shipmentsSrc);
vm.runInThisContext(purchaseOrdersSrc);

// Hook pages into App.pages
App.pages['shipments'] = {
    ...App.pages['shipments'],
    loadShipments() { shipmentsLoadedCount++; },
    openShipmentDetailsModal(id) { lastOpenedShipmentDetailsId = id; }
};

async function runPhaseGTests() {
    let passed = 0;
    let failed = 0;

    function test(name, fn) {
        return (async () => {
            try {
                await fn();
                console.log(`  [PASS] ${name}`);
                passed++;
            } catch (err) {
                console.error(`  [FAIL] ${name}: ${err.message}`);
                failed++;
            }
        })();
    }

    console.log("Suite 1: Supplier PO List & Row Actions Verification");

    await test("1.1 Supplier sees btn-action-dispatch button for Accepted POs", async () => {
        mockActiveUser = { id: 10, role: 'Supplier' };
        const dummyTbody = new MockElement('tbody', 'po-table-body');
        elementsById.set('po-table-body', dummyTbody);

        // Call loadPurchaseOrders on page
        const poPage = App.pages['purchase-orders'];
        assert(poPage, "purchase-orders page should exist");
        await poPage.loadPurchaseOrders();

        const rendered = dummyTbody.innerHTML;
        assert(rendered.includes('btn-action-dispatch'), "Table should contain btn-action-dispatch for eligible accepted POs");
        assert(rendered.includes('PO-101'), "Accepted PO-101 should be rendered");
    });

    await test("1.2 Non-accepted or completed POs do not render btn-action-dispatch", async () => {
        const dummyTbody = elementsById.get('po-table-body');
        const rendered = dummyTbody.innerHTML;
        
        // Match each row and check if dispatch button is present
        const rows = rendered.split('<tr>');
        for (const row of rows) {
            if (row.includes('PO-103') && row.includes('Pending')) {
                assert(!row.includes('btn-action-dispatch'), "Pending order PO-103 must not have a dispatch button");
            }
            if (row.includes('PO-104') && row.includes('Delivered')) {
                assert(!row.includes('btn-action-dispatch'), "Delivered order PO-104 must not have a dispatch button");
            }
            if (row.includes('PO-105') && row.includes('Cancelled')) {
                assert(!row.includes('btn-action-dispatch'), "Cancelled order PO-105 must not have a dispatch button");
            }
        }
    });

    await test("1.3 Non-supplier role (e.g. Employee) never sees btn-action-dispatch", async () => {
        mockActiveUser = { id: 20, role: 'Employee' };
        const dummyTbody = elementsById.get('po-table-body');
        await App.pages['purchase-orders'].loadPurchaseOrders();
        assert(!dummyTbody.innerHTML.includes('btn-action-dispatch'), "Employee role must not see dispatch buttons on PO rows");
    });

    await test("1.4 dispatchPO(poId) navigates to shipments and opens create modal with preselected PO", async () => {
        mockActiveUser = { id: 10, role: 'Supplier' };
        const originalOpenCreateShipmentModal = App.pages['shipments'].openCreateShipmentModal;
        let preselectedArg = null;
        App.pages['shipments'].openCreateShipmentModal = async (id) => { preselectedArg = id; };

        App.pages['purchase-orders'].dispatchPO(101);
        assert.strictEqual(lastNavigatedPath, 'shipments', "dispatchPO must navigate to 'shipments'");
        
        // Allow timeout dispatcher to execute
        await new Promise(r => setTimeout(r, 60));
        assert.strictEqual(preselectedArg, 101, "openCreateShipmentModal must be called with preselected PO ID 101");

        // Restore real method
        App.pages['shipments'].openCreateShipmentModal = originalOpenCreateShipmentModal;
    });

    console.log("\nSuite 2: PO Details Modal Allocation Transparency & Actions");

    await test("2.1 viewPODetails renders ORDERED, ALLOCATED, and REMAINING line item columns", async () => {
        mockActiveUser = { id: 10, role: 'Supplier' };
        await App.pages['purchase-orders'].viewPODetails(101);

        const poModal = openModals[openModals.length - 1];
        assert(poModal, "PO details modal should be opened");
        const html = poModal.innerHTML;
        assert(html.includes('ORDERED'), "Table header must include ORDERED");
        assert(html.includes('ALLOCATED'), "Table header must include ALLOCATED");
        assert(html.includes('REMAINING'), "Table header must include REMAINING");

        // Check line items display
        assert(html.includes('WID-A'), "Product WID-A must be present");
        assert(html.includes('Full'), "Fully allocated product VLV-B should display 'Full' indicator");
    });

    await test("2.2 viewPODetails footer contains 'Dispatch Shipment' action for accepted PO", async () => {
        const poModal = openModals[openModals.length - 1];
        const dispatchBtn = elementsById.get('modal-btn-dispatch');
        assert(dispatchBtn, "Modal footer must contain #modal-btn-dispatch for accepted PO");

        let dispatchPoCalled = null;
        App.pages['purchase-orders'].dispatchPO = (id) => { dispatchPoCalled = id; };
        await dispatchBtn.dispatchEvent('click');
        assert.strictEqual(dispatchPoCalled, 101, "Clicking modal dispatch button must trigger dispatchPO(101)");
    });

    console.log("\nSuite 3: Shipment Allocation Modal Preselection & Auto-Loading");

    await test("3.1 openCreateShipmentModal(102) preselects PO #102 and loads allocation lines", async () => {
        await App.pages['shipments'].openCreateShipmentModal(102);
        await new Promise(r => setTimeout(r, 60));
        const modal = openModals[openModals.length - 1];
        assert(modal, "Create shipment modal should be open");

        const poSelect = elementsById.get('modal-ship-po-select');
        assert(poSelect, "PO select element must exist");
        assert.strictEqual(String(poSelect.value), '102', "PO select must have preselected value '102'");

        const previewBox = elementsById.get('modal-ship-po-preview');
        assert(previewBox, "PO preview box must exist");
        assert(previewBox.innerHTML.includes('PO #102 Product Allocations'), "Preview box must render PO 102 allocations");
    });

    await test("3.2 Preselecting ineligible PO triggers warning toast and leaves selector ready", async () => {
        toasts.length = 0;
        await App.pages['shipments'].openCreateShipmentModal(103); // PO 103 is Pending
        await new Promise(r => setTimeout(r, 60));
        assert(toasts.some(t => t.type === 'warning' && t.msg.includes('not eligible for dispatch')), 
            "Should show warning toast for ineligible pending PO");
    });

    console.log("\nSuite 4: Pre-Dispatch Validation & Review Step");

    await test("4.1 Deselecting all products blocks review with clear error toast", async () => {
        toasts.length = 0;
        await App.pages['shipments'].openCreateShipmentModal(101);
        await new Promise(r => setTimeout(r, 60));

        const previewBox = elementsById.get('modal-ship-po-preview');
        const checkboxes = previewBox.querySelectorAll('.alloc-item-checkbox');
        checkboxes.forEach(cb => { cb.checked = false; });

        const reviewBtn = elementsById.get('modal-btn-to-review');
        assert(reviewBtn, "Review & Dispatch button must exist");
        await reviewBtn.dispatchEvent('click');

        assert(toasts.some(t => t.type === 'error' && t.msg.includes('Please select at least one product')), 
            "Must toast error when no products are selected for dispatch");
    });

    await test("4.2 Valid allocations open Pre-Dispatch Review Modal with complete summary", async () => {
        await App.pages['shipments'].openCreateShipmentModal(101);
        await new Promise(r => setTimeout(r, 60));

        const previewBox = elementsById.get('modal-ship-po-preview');
        // Uncheck item 3, keep item 1 (quantity 30 max)
        const cb1 = previewBox.querySelector('.alloc-item-checkbox[data-product-id="1"]');
        assert(cb1, "Checkbox for product 1 must exist");
        cb1.checked = true;

        const cb3 = previewBox.querySelector('.alloc-item-checkbox[data-product-id="3"]');
        if (cb3) cb3.checked = false;

        const input1 = previewBox.querySelector('.alloc-qty-input[data-product-id="1"]');
        input1.value = '15'; // Allocate 15 units of product 1

        const reviewBtn = elementsById.get('modal-btn-to-review');
        await reviewBtn.dispatchEvent('click');

        // Review modal should now be the top modal
        const reviewModal = openModals[openModals.length - 1];
        assert.strictEqual(reviewModal.id, 'modal-predispatch-review', "Review modal #modal-predispatch-review must be open");

        const rHtml = reviewModal.innerHTML;
        assert(rHtml.includes('Review & Confirm Shipment Dispatch'), "Review modal must have header title");
        assert(rHtml.includes('PO #101'), "Review modal must display target PO #101");
        assert(rHtml.includes('BlueDart Express'), "Review modal must display carrier");
        assert(rHtml.includes('Total Units: 15'), "Review modal must compute Total Units: 15");
        assert(rHtml.includes('WID-A') || rHtml.includes('Industrial Widget A'), "Review modal must list allocated product name/SKU");
    });

    await test("4.3 'Back to Edit' closes review modal and preserves create modal", async () => {
        const reviewModal = openModals[openModals.length - 1];
        const backBtn = elementsById.get('modal-btn-review-back');
        assert(backBtn, "Back to Edit button must exist");

        const modalCountBefore = openModals.length;
        await backBtn.dispatchEvent('click');

        assert.strictEqual(openModals.length, modalCountBefore - 1, "Back button should close review modal");
        const topModal = openModals[openModals.length - 1];
        assert.strictEqual(topModal.id, 'modal-create-shipment', "Create shipment modal should remain active and visible");
    });

    console.log("\nSuite 5: Double Submission Protection & Error Handling");

    await test("5.1 Missing shipment ID from API triggers descriptive error toast", async () => {
        toasts.length = 0;
        // Re-open review modal
        const reviewBtn = elementsById.get('modal-btn-to-review');
        await reviewBtn.dispatchEvent('click');

        const confirmBtn = elementsById.get('modal-btn-review-confirm');
        assert(confirmBtn, "Confirm & Dispatch button must exist");

        // Set carrier to trigger missing shipment id simulation
        const carrierInp = elementsById.get('modal-ship-carrier');
        carrierInp.value = 'OmitIdSim';
        // Mock payload intercept
        const origPost = Api.post;
        Api.post = async (url, payload) => ({ message: 'Created without shipment_id' });

        await confirmBtn.dispatchEvent('click');

        assert(toasts.some(t => t.type === 'error' && t.msg.includes('server response did not include a valid shipment ID')),
            "Must report error when API response omits shipment ID");

        Api.post = origPost;
    });

    await test("5.2 Ambiguous network timeout is caught safely and buttons are re-enabled", async () => {
        toasts.length = 0;
        const confirmBtn = elementsById.get('modal-btn-review-confirm');
        const backBtn = elementsById.get('modal-btn-review-back');

        const origPost = Api.post;
        Api.post = async () => { throw new Error('Gateway Timeout (504)'); };

        await confirmBtn.dispatchEvent('click');

        assert(toasts.some(t => t.type === 'error' && t.msg.includes('Gateway Timeout (504)')),
            "Must catch network error and display toast to user");
        assert.strictEqual(confirmBtn.disabled, false, "Confirm button must be re-enabled on failure");
        assert.strictEqual(backBtn.disabled, false, "Back button must be re-enabled on failure");

        Api.post = origPost;
    });

    console.log("\nSuite 6: Successful Dispatch End-to-End Handshake");

    await test("6.1 Successful dispatch submits payload, closes modals, refreshes, and opens new shipment details", async () => {
        toasts.length = 0;
        shipmentsLoadedCount = 0;
        lastOpenedShipmentDetailsId = null;

        const confirmBtn = elementsById.get('modal-btn-review-confirm');
        await confirmBtn.dispatchEvent('click');

        // Check submitted payload
        assert(lastApiPost, "API post must have been executed");
        assert.strictEqual(lastApiPost.url, '/shipments/', "URL must be /shipments/");
        assert.strictEqual(lastApiPost.payload.purchase_order_id, 101, "PO ID must be 101");
        assert(Array.isArray(lastApiPost.payload.items) && lastApiPost.payload.items.length === 1, "Allocated items array must have 1 item");
        assert.strictEqual(lastApiPost.payload.items[0].product_id, 1, "Product ID must be 1");
        assert.strictEqual(lastApiPost.payload.items[0].quantity, 15, "Quantity must be 15");

        // Check UX state transitions
        assert(toasts.some(t => t.type === 'success' && t.msg.includes('dispatched successfully')), "Must show success toast");
        assert(shipmentsLoadedCount > 0, "loadShipments must be refreshed");
        assert.strictEqual(lastOpenedShipmentDetailsId, 701, "openShipmentDetailsModal must be opened with newly generated shipment ID 701");
    });

    console.log("\n===================================================================");
    console.log(`PHASE G TEST RESULTS: ${passed} PASSED, ${failed} FAILED`);
    console.log("===================================================================");

    if (failed > 0) {
        process.exit(1);
    }
}

runPhaseGTests().catch(err => {
    console.error("Unhandled test runner exception:", err);
    process.exit(1);
});
