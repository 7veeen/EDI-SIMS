// scratch/test_frontend_system_status.js
const fs = require('fs');
const path = require('path');

// Mock DOM elements and document
class MockElement {
    constructor(id = '', tagName = 'div') {
        this.id = id;
        this.tagName = tagName;
        this.innerHTML = '';
        this.textContent = '';
        this.style = {};
        this.className = '';
        this.disabled = false;
        this._listeners = {};
    }

    addEventListener(event, fn) {
        this._listeners[event] = fn;
    }

    trigger(event) {
        if (this._listeners[event]) this._listeners[event]();
    }
}

const elements = {};
function getOrCreateElement(id, tagName = 'div') {
    if (!elements[id]) {
        elements[id] = new MockElement(id, tagName);
    }
    return elements[id];
}

global.document = {
    createElement(tag) {
        return new MockElement('', tag);
    },
    getElementById(id) {
        return getOrCreateElement(id);
    }
};

global.localStorage = {
    _data: { 'sims_token': 'mock.jwt.token' },
    getItem(k) { return this._data[k] || null; },
    setItem(k, v) { this._data[k] = v; },
    removeItem(k) { delete this._data[k]; }
};

global.API_BASE_URL = 'http://127.0.0.1:5000/api';

let lastToast = null;
global.Utils = {
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

let loggedOut = false;
global.Auth = {
    logout() {
        loggedOut = true;
    }
};

global.App = { pages: {} };

// Load system-status.js
const code = fs.readFileSync(path.join(__dirname, '..', 'frontend', 'js', 'pages', 'system-status.js'), 'utf8');
eval(code);

async function runTests() {
    console.log("=== SCENARIO 1: PAGE REGISTRATION & RENDER ===");
    const page = App.pages['system-status'];
    if (!page) throw new Error("system-status page not registered!");
    const container = page.render();
    if (!container.innerHTML.includes("System Health & Monitoring")) {
        throw new Error("Page render missing title!");
    }
    console.log("PASS: Page render successful.");

    console.log("\n=== SCENARIO 2: HEALTHY STATE (NORMAL LATENCY <= 500ms) ===");
    global.fetch = async () => ({
        status: 200,
        ok: true,
        json: async () => ({
            overall_status: "HEALTHY",
            backend: { status: "UP" },
            database: {
                status: "CONNECTED",
                latency_ms: 85.5,
                performance: "NORMAL",
                performance_warning: false
            },
            performance_warning: false,
            modules: [
                { name: "Inventory", status: "READY", progress: 100, message: "Inventory is ready", updated_at: "2026-10-11T10:00:00" }
            ],
            uptime_seconds: 3600,
            checked_at: "2026-10-11T10:00:00Z"
        })
    });

    await page.loadSystemHealth();
    console.log("Overall badge:", elements['system-overall-badge'].innerHTML);
    console.log("Overall val:", elements['val-overall'].textContent, "color:", elements['val-overall'].style.color);
    console.log("DB status:", elements['val-database'].textContent, "color:", elements['val-database'].style.color);
    console.log("DB latency:", elements['val-latency'].textContent);
    console.log("Warning banner display:", elements['perf-warning-banner'].style.display);
    if (!elements['system-overall-badge'].innerHTML.includes("SYSTEM HEALTHY")) throw new Error("Expected SYSTEM HEALTHY badge");
    if (elements['perf-warning-banner'].style.display !== 'none') throw new Error("Banner should be hidden");
    if (!elements['subsystems-tbody'].innerHTML.includes("Inventory")) throw new Error("Inventory module row missing");
    console.log("PASS: Healthy state rendered correctly.");

    console.log("\n=== SCENARIO 3: ELEVATED LATENCY (> 500ms) PERFORMANCE ADVISORY ===");
    global.fetch = async () => ({
        status: 200,
        ok: true,
        json: async () => ({
            overall_status: "DEGRADED",
            backend: { status: "UP" },
            database: {
                status: "CONNECTED",
                latency_ms: 720.0,
                performance: "ELEVATED",
                performance_warning: true
            },
            performance_warning: true,
            modules: [
                { name: "Inventory", status: "READY", progress: 100, message: "Inventory is ready", updated_at: "2026-10-11T10:00:00" }
            ],
            uptime_seconds: 3600,
            checked_at: "2026-10-11T10:00:00Z"
        })
    });

    await page.loadSystemHealth();
    console.log("Overall badge:", elements['system-overall-badge'].innerHTML);
    console.log("Overall val:", elements['val-overall'].textContent);
    console.log("Warning banner display:", elements['perf-warning-banner'].style.display);
    console.log("Banner latency:", elements['banner-latency-ms'].textContent);
    if (!elements['system-overall-badge'].innerHTML.includes("SYSTEM DEGRADED")) throw new Error("Expected SYSTEM DEGRADED badge");
    if (elements['perf-warning-banner'].style.display !== 'flex') throw new Error("Banner should be displayed");
    if (elements['banner-latency-ms'].textContent !== '720.00 ms') throw new Error("Banner latency mismatch");
    console.log("PASS: Elevated latency state rendered correctly.");

    console.log("\n=== SCENARIO 4: DATABASE DISCONNECTED (HTTP 503) ===");
    global.fetch = async () => ({
        status: 503,
        ok: false,
        json: async () => ({
            overall_status: "DEGRADED",
            backend: { status: "UP" },
            database: {
                status: "DISCONNECTED",
                latency_ms: null,
                performance: "UNAVAILABLE",
                performance_warning: false
            },
            performance_warning: false,
            modules: [],
            uptime_seconds: 3600,
            checked_at: "2026-10-11T10:00:00Z"
        })
    });

    await page.loadSystemHealth();
    console.log("Overall badge:", elements['system-overall-badge'].innerHTML);
    console.log("DB status:", elements['val-database'].textContent, "color:", elements['val-database'].style.color);
    console.log("Latency:", elements['val-latency'].textContent);
    console.log("Subsystems tbody:", elements['subsystems-tbody'].innerHTML);
    if (!elements['system-overall-badge'].innerHTML.includes("SYSTEM DEGRADED")) throw new Error("Expected SYSTEM DEGRADED badge");
    if (elements['val-database'].textContent !== "DISCONNECTED") throw new Error("Expected DISCONNECTED DB status");
    if (elements['val-database'].style.color !== "#ef4444") throw new Error("Expected red color for DISCONNECTED DB");
    console.log("PASS: Database disconnected state handled correctly.");

    console.log("\n=== SCENARIO 5: BACKEND NETWORK ERROR (SERVER OFFLINE) ===");
    global.fetch = async () => {
        throw new Error("Failed to fetch: Connection refused");
    };

    await page.loadSystemHealth();
    console.log("Overall badge:", elements['system-overall-badge'].innerHTML);
    console.log("Overall val:", elements['val-overall'].textContent);
    console.log("Backend val:", elements['val-backend'].textContent);
    console.log("Last toast:", lastToast);
    if (!elements['system-overall-badge'].innerHTML.includes("BACKEND OFFLINE")) throw new Error("Expected BACKEND OFFLINE badge");
    if (elements['val-overall'].textContent !== "UNREACHABLE") throw new Error("Expected UNREACHABLE overall");
    if (elements['val-backend'].textContent !== "DOWN") throw new Error("Expected DOWN backend");
    if (elements['btn-refresh-status'].disabled !== false) throw new Error("Refresh button should be re-enabled");
    console.log("PASS: Network failure handled gracefully.");

    console.log("\n=== SCENARIO 6: 401 UNAUTHORIZED / SESSION EXPIRED ===");
    loggedOut = false;
    global.fetch = async () => ({
        status: 401,
        ok: false
    });

    await page.loadSystemHealth();
    if (!loggedOut) throw new Error("Auth.logout() should have been called on 401");
    if (!lastToast || lastToast.type !== "error") throw new Error("Toast error expected on 401");
    console.log("PASS: 401 Unauthorized triggered logout and notification.");

    console.log("\n=== SCENARIO 7: 403 FORBIDDEN / ACCESS DENIED ===");
    global.fetch = async () => ({
        status: 403,
        ok: false
    });

    await page.loadSystemHealth();
    if (!elements['subsystems-tbody'].innerHTML.includes("Access denied")) {
        throw new Error("Access denied message expected in tbody");
    }
    console.log("PASS: 403 Forbidden rendered access denied state.");

    console.log("\n=== SCENARIO 8: XSS INJECTION DEFENSE IN TELEMETRY ===");
    global.fetch = async () => ({
        status: 200,
        ok: true,
        json: async () => ({
            overall_status: "HEALTHY",
            backend: { status: "UP" },
            database: { status: "CONNECTED", latency_ms: 50 },
            modules: [
                {
                    name: "<script>alert('xss-mod')</script>",
                    status: "<b onclick=alert(1)>PENDING</b>",
                    progress: 50,
                    message: "<img src=x onerror=alert('xss-msg')>",
                    updated_at: "2026-10-11T10:00:00"
                }
            ]
        })
    });

    await page.loadSystemHealth();
    const tableHtml = elements['subsystems-tbody'].innerHTML;
    if (tableHtml.includes("<script>") || tableHtml.includes("<img src=x") || tableHtml.includes("<b onclick")) {
        throw new Error("XSS vulnerability detected in subsystem rendering!");
    }
    if (!tableHtml.includes("&lt;script&gt;") || !tableHtml.includes("&lt;img src=x")) {
        throw new Error("HTML special characters were not escaped!");
    }
    console.log("PASS: XSS injection vectors neutralized via Utils.escapeHtml().");

    console.log("\n=== ALL FRONTEND DOM & SCENARIO TESTS PASSED SUCCESSFULLY! ===");
}

runTests().catch(err => {
    console.error("TEST FAILED:", err);
    process.exit(1);
});
