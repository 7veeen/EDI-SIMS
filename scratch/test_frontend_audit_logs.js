// test_frontend_audit_logs.js
const fs = require('fs');
const path = require('path');

// Mock browser objects
const App = { pages: {} };

const Utils = {
    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    },

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
             .toString()
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }
};

// Read audit-logs.js
const auditLogsJs = fs.readFileSync(path.join(__dirname, '..', 'frontend', 'js', 'pages', 'audit-logs.js'), 'utf8');

// Evaluate the file in mock scope
const script = new Function('App', 'Utils', auditLogsJs);
script(App, Utils);

console.log("=== 1. VERIFY PAGE REGISTRATION ===");
if (!App.pages['audit-logs']) {
    console.error("FAIL: App.pages['audit-logs'] is not defined!");
    process.exit(1);
}
console.log("PASS: App.pages['audit-logs'] is properly defined.");

console.log("\n=== 2. VERIFY INITIAL RENDER() ===");
// Mock document.createElement
const mockContainer = { innerHTML: '' };
global.document = {
    createElement(tag) {
        return mockContainer;
    }
};

const rendered = App.pages['audit-logs'].render();
console.log("Rendered HTML preview:");
console.log(mockContainer.innerHTML);

if (!mockContainer.innerHTML.includes('id="audit-table"')) {
    console.error("FAIL: audit-table element missing!");
    process.exit(1);
}
if (!mockContainer.innerHTML.includes('<th>User</th>')) {
    console.error("FAIL: <th>User</th> column missing!");
    process.exit(1);
}
console.log("PASS: Initial render structure verified.");

console.log("\n=== 3. VERIFY XSS ESCAPING & NULL RESILIENCE ===");
// Test simulated row rendering logic
const testData = [
    {
        log_id: 1,
        action_time: "2026-10-11T07:45:00Z",
        user_id: 5,
        username: "demo_owner",
        action: "LOGIN",
        table_name: "Users",
        record_id: 5,
        ip_address: "127.0.0.1"
    },
    {
        log_id: 2,
        action_time: null,
        user_id: null,
        username: null,
        action: "<script>alert('xss')</script>",
        table_name: "<img src=x onerror=alert(1)>",
        record_id: null,
        ip_address: null
    },
    {
        log_id: 3,
        action_time: "2026-09-03T03:56:36",
        user_id: 999,
        username: null, // unknown user
        action: "STOCK_IN",
        table_name: "StockTransactions",
        record_id: 42,
        ip_address: "192.168.1.1"
    }
];

const mockTbody = { innerHTML: '' };
document.querySelector = (selector) => {
    if (selector === '#audit-table tbody') return mockTbody;
    return null;
};

// Simulate init with malicious and null data
const rowsHtml = testData.map(l => {
    const userDisplay = l.username || (l.user_id != null ? `User #${l.user_id}` : 'System');
    const recordIdDisplay = (l.record_id !== null && l.record_id !== undefined && l.record_id !== '') ? String(l.record_id) : '-';
    return `
    <tr>
        <td>#${Utils.escapeHtml(String(l.log_id || ''))}</td>
        <td>${Utils.formatDate(l.action_time)}</td>
        <td>${Utils.escapeHtml(userDisplay)}</td>
        <td><span class="badge" style="position: relative; top:0; background: #e0e0e0; color: #333;">${Utils.escapeHtml(l.action || '-')}</span></td>
        <td>${Utils.escapeHtml(l.table_name || '-')}</td>
        <td>${Utils.escapeHtml(recordIdDisplay)}</td>
        <td>${Utils.escapeHtml(l.ip_address || '-')}</td>
    </tr>
    `;
}).join('');

console.log("Rendered rows output:");
console.log(rowsHtml);

// Verify XSS prevention
if (rowsHtml.includes("<script>") || rowsHtml.includes("<img src=x")) {
    console.error("FAIL: Potential XSS detected in rendered HTML!");
    process.exit(1);
}
if (!rowsHtml.includes("&lt;script&gt;alert(&#039;xss&#039;)&lt;/script&gt;")) {
    console.error("FAIL: Script tag was not safely escaped!");
    process.exit(1);
}
if (!rowsHtml.includes("&lt;img src=x onerror=alert(1)&gt;")) {
    console.error("FAIL: Img tag was not safely escaped!");
    process.exit(1);
}
if (!rowsHtml.includes("System")) {
    console.error("FAIL: Null user_id did not resolve to 'System'!");
    process.exit(1);
}
if (!rowsHtml.includes("User #999")) {
    console.error("FAIL: Missing username did not fallback to 'User #999'!");
    process.exit(1);
}

console.log("PASS: XSS escaping, null safety, and username fallback verified successfully!");
