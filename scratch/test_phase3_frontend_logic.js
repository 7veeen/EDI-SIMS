// scratch/test_phase3_frontend_logic.js
// Automated verification of Phase 3 Reports Page logic: search, sort, date filter, pagination, summary cards, and security escaping

const assert = require('assert');

// Mock Utils
const Utils = {
    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },
    formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        const d = new Date(dateStr);
        return isNaN(d.getTime()) ? 'N/A' : d.toLocaleDateString();
    }
};

// Mock Reports Controller based on reports.js logic
class ReportsPageTester {
    constructor() {
        this.allReports = [];
        this.filteredReports = [];
        this.searchQuery = '';
        this.startDate = '';
        this.endDate = '';
        this.snapshotFilter = 'all';
        this.sortField = 'report_id';
        this.sortDirection = 'desc';
        this.currentPage = 1;
        this.pageSize = 10;
    }

    setReports(reports) {
        this.allReports = [...reports];
        this.applyFiltersAndSort();
    }

    applyFiltersAndSort() {
        let list = [...this.allReports];

        // 1. Search Query
        if (this.searchQuery && this.searchQuery.trim()) {
            const q = this.searchQuery.toLowerCase().trim();
            list = list.filter(r => {
                const idStr = String(r.report_id);
                const nameStr = (r.report_name || '').toLowerCase();
                const typeStr = (r.report_type || '').toLowerCase();
                const userStr = (r.generated_by_username || '').toLowerCase();
                const userIdStr = String(r.generated_by || '');
                return idStr.includes(q) ||
                       nameStr.includes(q) ||
                       typeStr.includes(q) ||
                       userStr.includes(q) ||
                       userIdStr.includes(q);
            });
        }

        // 2. Date Range Filter
        if (this.startDate) {
            const start = new Date(this.startDate + 'T00:00:00');
            if (!isNaN(start.getTime())) {
                list = list.filter(r => {
                    if (!r.generated_on) return false;
                    const d = new Date(r.generated_on);
                    return !isNaN(d.getTime()) && d >= start;
                });
            }
        }

        if (this.endDate) {
            const end = new Date(this.endDate + 'T23:59:59.999');
            if (!isNaN(end.getTime())) {
                list = list.filter(r => {
                    if (!r.generated_on) return false;
                    const d = new Date(r.generated_on);
                    return !isNaN(d.getTime()) && d <= end;
                });
            }
        }

        // 3. Snapshot Filter
        if (this.snapshotFilter === 'saved') {
            list = list.filter(r => Boolean(r.has_snapshot));
        } else if (this.snapshotFilter === 'legacy') {
            list = list.filter(r => !r.has_snapshot);
        }

        // 4. Sorting
        list.sort((a, b) => {
            let valA, valB;
            if (this.sortField === 'report_id') {
                valA = Number(a.report_id) || 0;
                valB = Number(b.report_id) || 0;
                return this.sortDirection === 'asc' ? valA - valB : valB - valA;
            } else if (this.sortField === 'generated_on') {
                valA = a.generated_on ? new Date(a.generated_on).getTime() : 0;
                valB = b.generated_on ? new Date(b.generated_on).getTime() : 0;
                return this.sortDirection === 'asc' ? valA - valB : valB - valA;
            } else if (this.sortField === 'has_snapshot') {
                valA = a.has_snapshot ? 1 : 0;
                valB = b.has_snapshot ? 1 : 0;
                return this.sortDirection === 'asc' ? valA - valB : valB - valA;
            } else if (this.sortField === 'generated_by') {
                valA = (a.generated_by_username || String(a.generated_by) || '').toLowerCase();
                valB = (b.generated_by_username || String(b.generated_by) || '').toLowerCase();
                const cmp = valA.localeCompare(valB);
                return this.sortDirection === 'asc' ? cmp : -cmp;
            } else {
                valA = (a[this.sortField] || '').toLowerCase();
                valB = (b[this.sortField] || '').toLowerCase();
                const cmp = valA.localeCompare(valB);
                return this.sortDirection === 'asc' ? cmp : -cmp;
            }
        });

        this.filteredReports = list;

        // Clamp current page
        const totalPages = Math.ceil(this.filteredReports.length / this.pageSize) || 1;
        if (this.currentPage > totalPages) {
            this.currentPage = totalPages;
        }
        if (this.currentPage < 1) {
            this.currentPage = 1;
        }
    }

    getPageItems() {
        const startIdx = (this.currentPage - 1) * this.pageSize;
        return this.filteredReports.slice(startIdx, startIdx + this.pageSize);
    }

    getSummaryStats() {
        return {
            total: this.allReports.length,
            saved: this.allReports.filter(r => r.has_snapshot).length,
            legacy: this.allReports.filter(r => !r.has_snapshot).length,
            matching: this.filteredReports.length
        };
    }

    resetFilters() {
        this.searchQuery = '';
        this.startDate = '';
        this.endDate = '';
        this.snapshotFilter = 'all';
        this.sortField = 'report_id';
        this.sortDirection = 'desc';
        this.currentPage = 1;
        this.applyFiltersAndSort();
    }
}

// Sample Test Data: 25 mock reports with mixed dates, creators, and snapshot status
const mockReports = [
    { report_id: 1, report_name: 'Monthly Inventory A', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-01T10:00:00Z', has_snapshot: false },
    { report_id: 2, report_name: 'Weekly Warehouse Audit', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-02T11:00:00Z', has_snapshot: false },
    { report_id: 3, report_name: 'Quarterly Review', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-03T12:00:00Z', has_snapshot: false },
    { report_id: 4, report_name: 'Special Electronic Stock', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-04T13:00:00Z', has_snapshot: true },
    { report_id: 5, report_name: 'Logistics Balance', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-05T14:00:00Z', has_snapshot: true },
    { report_id: 6, report_name: 'Mid-Month Snapshot', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-06T15:00:00Z', has_snapshot: true },
    { report_id: 7, report_name: 'Safety Stock Check', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-07T16:00:00Z', has_snapshot: false },
    { report_id: 8, report_name: 'Hardware Components', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-08T17:00:00Z', has_snapshot: true },
    { report_id: 9, report_name: 'Packaging Stock Count', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-09T18:00:00Z', has_snapshot: false },
    { report_id: 10, report_name: 'Current Inventory Balance', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-10T08:00:00Z', has_snapshot: true },
    { report_id: 11, report_name: 'Office Supplies Stock', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-10T09:00:00Z', has_snapshot: true },
    { report_id: 12, report_name: 'Peripherals Count', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-10T10:00:00Z', has_snapshot: true },
    { report_id: 13, report_name: 'Spare Parts Valuation', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-10T11:00:00Z', has_snapshot: true },
    { report_id: 14, report_name: 'Raw Materials Count', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-10T12:00:00Z', has_snapshot: true },
    { report_id: 15, report_name: 'Finished Goods Audit', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-10T13:00:00Z', has_snapshot: true },
    { report_id: 16, report_name: 'High Priority Reserve', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-10T14:00:00Z', has_snapshot: true },
    { report_id: 17, report_name: 'Damaged Goods Write-off', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-10T15:00:00Z', has_snapshot: true },
    { report_id: 18, report_name: 'Return To Vendor Audit', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-10T16:00:00Z', has_snapshot: true },
    { report_id: 19, report_name: 'Quarantine Inventory', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-10T17:00:00Z', has_snapshot: true },
    { report_id: 20, report_name: 'Annual Reconciliation', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-10T18:00:00Z', has_snapshot: true },
    { report_id: 21, report_name: 'Q4 Pre-Audit Report', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-10T19:00:00Z', has_snapshot: true },
    { report_id: 22, report_name: 'Emergency Restock Audit', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-10T20:00:00Z', has_snapshot: true },
    { report_id: 23, report_name: 'Consignment Stock', report_type: 'Inventory', generated_by: 6, generated_by_username: 'demo_manager', generated_on: '2026-10-10T21:00:00Z', has_snapshot: true },
    { report_id: 24, report_name: 'Transit Stock Verification', report_type: 'Inventory', generated_by: 5, generated_by_username: 'demo_owner', generated_on: '2026-10-10T22:00:00Z', has_snapshot: true },
    { report_id: 25, report_name: '<script>alert(1)</script> Malicious Name', report_type: 'Inventory', generated_by: 6, generated_by_username: '<b>hacker</b>', generated_on: '2026-10-10T23:00:00Z', has_snapshot: true }
];

function runTests() {
    console.log("=== RUNNING PHASE 3 FRONTEND LOGIC TEST SUITE ===");
    const app = new ReportsPageTester();
    app.setReports(mockReports);

    // 1. Initial State & Summary Cards
    console.log("\n--- Test 1: Summary Cards Calculation ---");
    const stats = app.getSummaryStats();
    assert.strictEqual(stats.total, 25, "Total reports count must be 25");
    assert.strictEqual(stats.saved, 20, "Saved snapshot reports count must be 20");
    assert.strictEqual(stats.legacy, 5, "Legacy reports count must be 5");
    assert.strictEqual(stats.matching, 25, "Matching count initially equals total");
    console.log("  [PASS] Summary stats match expected counts (Total=25, Saved=20, Legacy=5, Matching=25)");

    // 2. Default Sorting (ID descending)
    console.log("\n--- Test 2: Default Sorting (ID desc) ---");
    const page1 = app.getPageItems();
    assert.strictEqual(page1.length, 10, "Default page size is 10");
    assert.strictEqual(page1[0].report_id, 25, "First item should be highest ID (25)");
    assert.strictEqual(page1[9].report_id, 16, "10th item should be ID 16");
    console.log("  [PASS] Default sort orders IDs 25 down to 16 on page 1");

    // 3. Search by Name
    console.log("\n--- Test 3: Search by Report Name ---");
    app.searchQuery = "hardware";
    app.applyFiltersAndSort();
    assert.strictEqual(app.filteredReports.length, 1);
    assert.strictEqual(app.filteredReports[0].report_id, 8);
    console.log("  [PASS] Search 'hardware' correctly isolated Report #8");

    // 4. Search by Creator Username
    console.log("\n--- Test 4: Search by Creator Username ---");
    app.searchQuery = "demo_owner";
    app.applyFiltersAndSort();
    assert.strictEqual(app.filteredReports.length, 12);
    app.filteredReports.forEach(r => assert.strictEqual(r.generated_by_username, 'demo_owner'));
    console.log("  [PASS] Search 'demo_owner' correctly isolated all 12 Owner reports");

    // 5. Search by Report ID
    console.log("\n--- Test 5: Search by Report ID ---");
    app.searchQuery = "17";
    app.applyFiltersAndSort();
    assert.strictEqual(app.filteredReports.length, 1);
    assert.strictEqual(app.filteredReports[0].report_id, 17);
    console.log("  [PASS] Search '17' isolated Report #17");

    // 6. Search with No Results State
    console.log("\n--- Test 6: Search with No Results ---");
    app.searchQuery = "NonExistentReportXYZ";
    app.applyFiltersAndSort();
    assert.strictEqual(app.filteredReports.length, 0);
    assert.strictEqual(app.getPageItems().length, 0);
    console.log("  [PASS] Non-matching search produces empty list (triggering no-results UI)");

    // 7. Reset Filters
    console.log("\n--- Test 7: Reset Filters Action ---");
    app.resetFilters();
    assert.strictEqual(app.searchQuery, '');
    assert.strictEqual(app.filteredReports.length, 25);
    console.log("  [PASS] Reset restored all 25 reports");

    // 8. Date Range Filtering
    console.log("\n--- Test 8: Date Range Filtering ---");
    app.startDate = '2026-10-01';
    app.endDate = '2026-10-05';
    app.applyFiltersAndSort();
    assert.strictEqual(app.filteredReports.length, 5, "Dates Oct 1 to Oct 5 should yield exactly 5 reports");
    const ids = app.filteredReports.map(r => r.report_id).sort((a,b) => a-b);
    assert.deepStrictEqual(ids, [1, 2, 3, 4, 5]);
    console.log("  [PASS] Date range 2026-10-01 to 2026-10-05 matched Reports #1–#5");

    // 9. Snapshot Type Filter
    console.log("\n--- Test 9: Snapshot Type Filter ---");
    app.resetFilters();
    app.snapshotFilter = 'legacy';
    app.applyFiltersAndSort();
    assert.strictEqual(app.filteredReports.length, 5);
    app.filteredReports.forEach(r => assert.strictEqual(r.has_snapshot, false));
    console.log("  [PASS] Snapshot filter 'legacy' isolated the 5 legacy reports");

    app.snapshotFilter = 'saved';
    app.applyFiltersAndSort();
    assert.strictEqual(app.filteredReports.length, 20);
    app.filteredReports.forEach(r => assert.strictEqual(r.has_snapshot, true));
    console.log("  [PASS] Snapshot filter 'saved' isolated the 20 saved reports");

    // 10. Sorting by Name Ascending & Descending
    console.log("\n--- Test 10: Sorting by Name ---");
    app.resetFilters();
    app.sortField = 'report_name';
    app.sortDirection = 'asc';
    app.applyFiltersAndSort();
    assert.strictEqual(app.filteredReports[0].report_name.startsWith('<script>'), true); // Special chars first in ASCII
    
    app.sortDirection = 'desc';
    app.applyFiltersAndSort();
    assert.strictEqual(app.filteredReports[0].report_name, 'Weekly Warehouse Audit');
    console.log("  [PASS] Alphabetical sorting works both ascending and descending");

    // 11. Pagination Navigation and Clamping
    console.log("\n--- Test 11: Pagination Navigation ---");
    app.resetFilters();
    app.pageSize = 10;
    assert.strictEqual(app.filteredReports.length, 25);
    // Page 1
    app.currentPage = 1;
    let items = app.getPageItems();
    assert.strictEqual(items.length, 10);
    assert.strictEqual(items[0].report_id, 25);
    assert.strictEqual(items[9].report_id, 16);
    // Page 2
    app.currentPage = 2;
    items = app.getPageItems();
    assert.strictEqual(items.length, 10);
    assert.strictEqual(items[0].report_id, 15);
    assert.strictEqual(items[9].report_id, 6);
    // Page 3
    app.currentPage = 3;
    items = app.getPageItems();
    assert.strictEqual(items.length, 5);
    assert.strictEqual(items[0].report_id, 5);
    assert.strictEqual(items[4].report_id, 1);
    console.log("  [PASS] 25 items cleanly paginate across 3 pages (10, 10, 5 items)");

    // Page Clamping when Filter narrows result set
    app.currentPage = 3;
    app.searchQuery = "Weekly";
    app.applyFiltersAndSort();
    assert.strictEqual(app.currentPage, 1, "Page must clamp to 1 when filtered count is only 1");
    console.log("  [PASS] Page clamping automatically restored currentPage to 1 upon narrowing filter");

    // 12. Security & HTML Escaping
    console.log("\n--- Test 12: Security & HTML Escaping ---");
    const malicious = mockReports.find(r => r.report_id === 25);
    const escapedName = Utils.escapeHtml(malicious.report_name);
    const escapedUser = Utils.escapeHtml(malicious.generated_by_username);
    assert.strictEqual(escapedName, '&lt;script&gt;alert(1)&lt;/script&gt; Malicious Name');
    assert.strictEqual(escapedUser, '&lt;b&gt;hacker&lt;/b&gt;');
    assert.strictEqual(escapedName.includes('<script>'), false);
    assert.strictEqual(escapedUser.includes('<b>'), false);
    console.log("  [PASS] Database-sourced strings with HTML/XSS payloads safely sanitized");

    console.log("\n>>> ALL PHASE 3 FRONTEND LOGIC TESTS PASSED SUCCESSFULLY! <<<");
}

runTests();
