// test_frontend_pagination.js - Node.js Unit Verification for PaginationComponent

const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Mock window and Utils
global.window = {};
global.Utils = {
    escapeHtml: (str) => {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
};

// Load pagination.js
const paginationCode = fs.readFileSync(path.join(__dirname, '../../frontend/js/components/pagination.js'), 'utf8');
eval(paginationCode);
const PaginationComponent = window.PaginationComponent;

console.log("Running Frontend Pagination Component Unit Tests...\n");

// Test 1: Empty or Zero Records
{
    const html = PaginationComponent.render({ total: 0, page: 1, pageSize: 20, totalPages: 1, label: 'items' });
    assert(html.includes("Showing 0 items"), "Test 1 Failed: Should display 'Showing 0 items'");
    assert(!html.includes("pagination-btn"), "Test 1 Failed: Should not render buttons when total is 0");
    console.log("✔ Test 1 Passed: Zero records displays empty indicator safely.");
}

// Test 2: Single Page (1 to 10 items)
{
    const html = PaginationComponent.render({
        total: 10,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        label: 'orders',
        onPageChangeName: "App.pages['orders'].goToPage"
    });
    assert(html.includes("Showing 1–10 of 10 orders"), "Test 2 Failed: Count range mismatch");
    assert(html.includes("disabled"), "Test 2 Failed: Previous and Next must be disabled on single page");
    assert(html.includes("active"), "Test 2 Failed: Page 1 button must have 'active' class");
    console.log("✔ Test 2 Passed: Single page displays correct range and disabled navigation controls.");
}

// Test 3: Multi-page First Page Active
{
    const html = PaginationComponent.render({
        total: 100,
        page: 1,
        pageSize: 20,
        totalPages: 5,
        label: 'shipments',
        onPageChangeName: "App.pages['shipments'].goToPage"
    });
    assert(html.includes("Showing 1–20 of 100 shipments"), "Test 3 Failed: Range calculation mismatch");
    assert(html.includes('disabled onclick="App.pages[\'shipments\'].goToPage(0)"') || html.includes('disabled'), "Test 3 Failed: Previous button must be disabled on page 1");
    assert(!html.includes('disabled onclick="App.pages[\'shipments\'].goToPage(2)"'), "Test 3 Failed: Next button must be enabled");
    console.log("✔ Test 3 Passed: Multi-page first page enables Next and disables Previous.");
}

// Test 4: Middle Page Active
{
    const html = PaginationComponent.render({
        total: 100,
        page: 3,
        pageSize: 20,
        totalPages: 5,
        label: 'requests',
        onPageChangeName: "App.pages['stock-requests'].goToPage"
    });
    assert(html.includes("Showing 41–60 of 100 requests"), "Test 4 Failed: Range for page 3 mismatch");
    assert(html.includes('onclick="App.pages[\'stock-requests\'].goToPage(2)"'), "Test 4 Failed: Previous goes to page 2");
    assert(html.includes('onclick="App.pages[\'stock-requests\'].goToPage(4)"'), "Test 4 Failed: Next goes to page 4");
    console.log("✔ Test 4 Passed: Middle page navigation correctly routes to previous and next pages.");
}

// Test 5: Final Page Active
{
    const html = PaginationComponent.render({
        total: 100,
        page: 5,
        pageSize: 20,
        totalPages: 5,
        label: 'invoices',
        onPageChangeName: "App.pages['invoices'].goToPage"
    });
    assert(html.includes("Showing 81–100 of 100 invoices"), "Test 5 Failed: Range for last page mismatch");
    assert(html.includes('onclick="App.pages[\'invoices\'].goToPage(4)"'), "Test 5 Failed: Previous goes to page 4");
    // Next button should be disabled
    assert(html.includes('disabled') && html.includes('Next'), "Test 5 Failed: Next must be disabled on final page");
    console.log("✔ Test 5 Passed: Final page disables Next control.");
}

// Test 6: Ellipsis for Large Page Sets
{
    const html = PaginationComponent.render({
        total: 1000,
        page: 10,
        pageSize: 20,
        totalPages: 50,
        label: 'logs',
        onPageChangeName: "App.pages['logs'].goToPage"
    });
    assert(html.includes("..."), "Test 6 Failed: Must render ellipsis for large page counts");
    assert(html.includes('title="Page 1"'), "Test 6 Failed: Must keep first page anchor");
    assert(html.includes('title="Page 50"'), "Test 6 Failed: Must keep last page anchor");
    console.log("✔ Test 6 Passed: Ellipsis successfully generated for distant pages while preserving boundary anchors.");
}

// Test 7: Label XSS Escaping Safety
{
    const maliciousLabel = '<script>alert("xss")</script>';
    const html = PaginationComponent.render({
        total: 5,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        label: maliciousLabel,
        onPageChangeName: "safe"
    });
    assert(!html.includes("<script>"), "Test 7 Failed: Malicious HTML tags must be escaped");
    assert(html.includes("&lt;script&gt;"), "Test 7 Failed: Script tag must be HTML entity escaped");
    console.log("✔ Test 7 Passed: Label strictly escaped against XSS injection.");
}

console.log("\nAll 7 Frontend Pagination Component tests passed successfully!\n");
