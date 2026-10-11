// scratch/test_frontend_backups.js
const fs = require('fs');
const path = require('path');

// Mock DOM environment
const App = { pages: {} };

const Utils = {
    formatDate(dateString) {
        if (!dateString) return '-';
        const d = new Date(dateString);
        return isNaN(d.getTime()) ? '-' : d.toLocaleDateString('en-US', {
            year: 'numeric', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    },
    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe.toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    },
    showToast(msg, type) {
        lastToast = { msg, type };
    }
};

let lastToast = null;
const Auth = {
    getUser() {
        return { id: 5, username: "demo_owner", role: "Owner" };
    }
};

const mockTbody = { innerHTML: '' };
const mockBtn = { disabled: false, innerHTML: '', addEventListener: () => {} };
global.document = {
    createElement(tag) {
        return { innerHTML: '' };
    },
    querySelector(sel) {
        if (sel === '#backups-table tbody') return mockTbody;
        return null;
    },
    getElementById(id) {
        if (id === 'btn-create-backup') return mockBtn;
        return null;
    }
};

// Read backups.js
const backupsJs = fs.readFileSync(path.join(__dirname, '..', 'frontend', 'js', 'pages', 'backups.js'), 'utf8');
const script = new Function('App', 'Utils', 'Auth', 'Api', 'document', backupsJs);

let mockApiData = [];
const Api = {
    async get(endpoint) {
        return mockApiData;
    },
    async post(endpoint, data) {
        return { message: "Backup created successfully", backup_name: "test.json" };
    }
};

script(App, Utils, Auth, Api, global.document);

console.log("=== 1. VERIFY PAGE REGISTRATION & RENDER ===");
if (!App.pages['backups']) throw new Error("backups page is not registered!");
const container = App.pages['backups'].render();
console.log("PASS: Page registered and render() returned container.");

console.log("\n=== 2. VERIFY LOAD BACKUPS WITH DATA ===");
mockApiData = [
    {
        backup_id: 15,
        backup_name: "inventory_backup_20261011_155210.json",
        backup_type: "Full",
        backup_size: "6.32 MB",
        backup_date: "2026-10-11T10:21:54Z",
        status: "Success",
        created_by: 5,
        creator_username: "demo_owner"
    },
    {
        backup_id: 16,
        backup_name: "<script>alert('xss')</script>",
        backup_type: "<img src=x onerror=alert(1)>",
        backup_size: "10 KB",
        backup_date: null,
        status: "Failed",
        created_by: 999
    }
];

App.pages['backups'].loadBackups().then(() => {
    console.log("Rendered tbody output:");
    console.log(mockTbody.innerHTML);

    if (!mockTbody.innerHTML.includes("#15")) throw new Error("Backup #15 missing");
    if (!mockTbody.innerHTML.includes("inventory_backup_20261011_155210.json")) throw new Error("Backup name missing");
    if (!mockTbody.innerHTML.includes("status-active")) throw new Error("Success status badge missing");
    if (!mockTbody.innerHTML.includes("status-inactive")) throw new Error("Failed status badge missing");
    
    // Check XSS escaping
    if (mockTbody.innerHTML.includes("<script>") || mockTbody.innerHTML.includes("<img src=x")) {
        console.error("FAIL: Raw HTML tag detected in backup table!");
        process.exit(1);
    }
    console.log("PASS: Backup history rendering and XSS protection verified.");
});
