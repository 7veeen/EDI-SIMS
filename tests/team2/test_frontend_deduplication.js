/**
 * test_frontend_deduplication.js
 * Verification test suite for SIMS Phase 2 Step 3:
 * Frontend Request Deduplication, Redundant Initialization Removal & Lifecycle Safety
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log("=================================================================");
console.log("SIMS PHASE 2 STEP 3: FRONTEND REQUEST DEDUPLICATION VERIFICATION");
console.log("=================================================================\n");

// Mock browser globals for Node.js execution
global.localStorage = {
    _data: {},
    getItem(key) { return this._data[key] || null; },
    setItem(key, val) { this._data[key] = String(val); },
    removeItem(key) { delete this._data[key]; },
    clear() { this._data = {}; }
};

let loggedOut = false;
global.Auth = {
    isAuthenticated() { return !!localStorage.getItem('sims_token'); },
    logout() {
        loggedOut = true;
        if (typeof Api !== 'undefined' && typeof Api.clearInFlightRequests === 'function') {
            Api.clearInFlightRequests();
        }
        localStorage.clear();
    }
};

// Load api.js
const apiCode = fs.readFileSync(path.join(__dirname, '..', '..', 'frontend/js/api/api.js'), 'utf8');
const vm = require('vm');
vm.runInThisContext(apiCode); // Evaluates const Api in the current context, or attach
if (typeof Api === 'undefined') {
    global.Api = eval(apiCode + '; Api;');
} else {
    global.Api = Api;
}

// Helper: delayed mock fetch
let fetchCalls = [];
let fetchHandler = null;

global.fetch = async (url, options) => {
    fetchCalls.push({ url, options });
    if (fetchHandler) {
        return fetchHandler(url, options);
    }
    return {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({ success: true })
    };
};

async function runTests() {
    // -------------------------------------------------------------
    // Test 1: In-Flight Deduplication for Concurrent GET Requests
    // -------------------------------------------------------------
    console.log("Test 1: Concurrent identical GET requests share a single in-flight promise...");
    localStorage.setItem('sims_token', 'jwt_token_user_1');
    fetchCalls = [];

    // Simulate async network delay
    fetchHandler = async (url, options) => {
        await new Promise(r => setTimeout(r, 30));
        return {
            ok: true,
            status: 200,
            statusText: 'OK',
            json: async () => ({ unread_count: 5 })
        };
    };

    const req1 = Api.get('/notifications/unread-count');
    const req2 = Api.get('/notifications/unread-count');

    // Both should receive the exact same promise
    assert.strictEqual(req1, req2, "Concurrent identical GET requests must share the identical pending promise");

    const [res1, res2] = await Promise.all([req1, req2]);
    assert.strictEqual(res1.unread_count, 5);
    assert.strictEqual(res2.unread_count, 5);
    assert.strictEqual(fetchCalls.length, 1, "Exactly one network fetch must be executed for concurrent identical GET requests");
    assert.strictEqual(Api._inFlightRequests.size, 0, "In-flight map must be empty after promise resolves");
    console.log("✓ Test 1 passed: 1 network fetch served 2 callers, in-flight map cleaned up.\n");

    // -------------------------------------------------------------
    // Test 2: Sequential Requests After Resolution Make Fresh Calls
    // -------------------------------------------------------------
    console.log("Test 2: Sequential GET requests after completion execute fresh fetches...");
    fetchCalls = [];
    const res3 = await Api.get('/notifications/unread-count');
    assert.strictEqual(fetchCalls.length, 1, "Sequential request must execute a new fetch");
    assert.strictEqual(Api._inFlightRequests.size, 0, "In-flight map must remain empty after request completion");
    console.log("✓ Test 2 passed: Sequential requests correctly bypass completed in-flight entries.\n");

    // -------------------------------------------------------------
    // Test 3: Failed Requests Clean Up In-Flight Map and Allow Retries
    // -------------------------------------------------------------
    console.log("Test 3: Failed requests immediately clean up in-flight entries and allow retries...");
    fetchCalls = [];
    fetchHandler = async (url, options) => {
        await new Promise(r => setTimeout(r, 20));
        return {
            ok: false,
            status: 500,
            statusText: 'Internal Server Error',
            json: async () => ({ error: 'Database timeout' })
        };
    };

    let caughtError = null;
    try {
        await Api.get('/dashboard/owner');
    } catch (e) {
        caughtError = e;
    }
    assert(caughtError, "Failed request must throw");
    assert.strictEqual(caughtError.status, 500);
    assert.strictEqual(Api._inFlightRequests.size, 0, "In-flight map must be cleaned up on failure");

    // Now retry with successful response
    fetchCalls = [];
    fetchHandler = async (url, options) => {
        return {
            ok: true,
            status: 200,
            statusText: 'OK',
            json: async () => ({ total_products: 42 })
        };
    };

    const retryRes = await Api.get('/dashboard/owner');
    assert.strictEqual(retryRes.total_products, 42);
    assert.strictEqual(fetchCalls.length, 1, "Retry must successfully trigger a new fetch");
    console.log("✓ Test 3 passed: In-flight tracker cleared on rejection, retry executed cleanly.\n");

    // -------------------------------------------------------------
    // Test 4: Different URLs and Parameters Are Never Merged
    // -------------------------------------------------------------
    console.log("Test 4: Different endpoints or query parameters are never merged...");
    fetchCalls = [];
    fetchHandler = async (url, options) => {
        await new Promise(r => setTimeout(r, 25));
        return {
            ok: true,
            status: 200,
            statusText: 'OK',
            json: async () => ({ data: url })
        };
    };

    const p1 = Api.get('/products/?page=1');
    const p2 = Api.get('/products/?page=2');
    assert.notStrictEqual(p1, p2, "Different query parameters must NOT share the same promise");

    const [r1, r2] = await Promise.all([p1, p2]);
    assert.strictEqual(fetchCalls.length, 2, "Two distinct fetches must be dispatched");
    assert(r1.data.includes('page=1'));
    assert(r2.data.includes('page=2'));
    console.log("✓ Test 4 passed: Distinct endpoints/parameters execute independently.\n");

    // -------------------------------------------------------------
    // Test 5: Different Auth Contexts Are Never Merged
    // -------------------------------------------------------------
    console.log("Test 5: Requests from different user authentication tokens are never merged...");
    fetchCalls = [];
    localStorage.setItem('sims_token', 'token_user_A');
    const userAReq = Api.get('/notifications/unread-count');

    // Simulate concurrent context from another user
    localStorage.setItem('sims_token', 'token_user_B');
    const userBReq = Api.get('/notifications/unread-count');

    assert.notStrictEqual(userAReq, userBReq, "Requests with different auth tokens must NOT share promises");
    await Promise.all([userAReq, userBReq]);
    assert.strictEqual(fetchCalls.length, 2, "Both user contexts must be dispatched separately");
    console.log("✓ Test 5 passed: User token context isolation verified.\n");

    // -------------------------------------------------------------
    // Test 6: Mutation Requests (POST, PUT, PATCH, DELETE) Are NEVER Deduplicated
    // -------------------------------------------------------------
    console.log("Test 6: Mutations (POST, PUT, PATCH, DELETE) are NEVER deduplicated...");
    fetchCalls = [];
    fetchHandler = async (url, options) => {
        await new Promise(r => setTimeout(r, 20));
        return {
            ok: true,
            status: 200,
            statusText: 'OK',
            json: async () => ({ id: Math.random() })
        };
    };

    const post1 = Api.post('/payments', { amount: 100 });
    const post2 = Api.post('/payments', { amount: 100 });
    assert.notStrictEqual(post1, post2, "Mutations must never share promises");

    const patch1 = Api.patch('/notifications/1/read');
    const patch2 = Api.patch('/notifications/1/read');
    assert.notStrictEqual(patch1, patch2, "PATCH mutations must never share promises");

    await Promise.all([post1, post2, patch1, patch2]);
    assert.strictEqual(fetchCalls.length, 4, "All 4 mutation requests must be dispatched individually");
    console.log("✓ Test 6 passed: Mutations are never deduplicated.\n");

    // -------------------------------------------------------------
    // Test 7: Logout Clears In-Flight State
    // -------------------------------------------------------------
    console.log("Test 7: Logout clears client-side in-flight tracker...");
    fetchHandler = async () => new Promise(r => setTimeout(r, 100)); // Pending
    const pendingPromise = Api.get('/reports/status');
    pendingPromise.catch(() => {}); // Prevent unhandled rejection
    assert(Api._inFlightRequests.size > 0, "Map must have in-flight entry");

    Auth.logout();
    assert.strictEqual(Api._inFlightRequests.size, 0, "Auth.logout() must clear all in-flight request entries");
    console.log("✓ Test 7 passed: In-flight map wiped out on logout.\n");

    // -------------------------------------------------------------
    // Test 8: Verify App.notifications.init() Removal of Redundant Call
    // -------------------------------------------------------------
    console.log("Test 8: Verify App.js notifications controller does not duplicate unread count...");
    const appCode = fs.readFileSync(path.join(__dirname, '..', '..', 'frontend/js/app.js'), 'utf8');
    assert(!appCode.includes('async init() {\n            this.setupDropdownListeners();\n            await this.updateUnreadCount();'),
        "App.notifications.init must not redundantly await updateUnreadCount()");
    assert(appCode.includes('// Note: Initial unread count is authoritatively fetched by App.navigate()'),
        "App.notifications.init must document authoritative single fetch in App.navigate");
    console.log("✓ Test 8 passed: Redundant startup unread count fetch removed.\n");

    console.log("=================================================================");
    console.log("ALL 8 FRONTEND REQUEST DEDUPLICATION TESTS PASSED SUCCESSFULLY!");
    console.log("=================================================================");
}

runTests().catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
