import asyncio
import json
import urllib.request
import websockets

async def send_cmd(ws, msg_id, method, params=None):
    payload = {"id": msg_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(payload))
    while True:
        resp = await ws.recv()
        data = json.loads(resp)
        if data.get("id") == msg_id:
            return data.get("result", {})

async def eval_js(ws, msg_id, expr):
    res = await send_cmd(ws, msg_id, "Runtime.evaluate", {
        "expression": expr,
        "awaitPromise": True,
        "returnByValue": True
    })
    return res.get("result", {}).get("value")

async def main():
    targets = json.loads(urllib.request.urlopen("http://localhost:9222/json").read())
    page_target = next(t for t in targets if t.get("type") == "page" and "8000" in t.get("url", ""))
    ws_url = page_target["webSocketDebuggerUrl"]
    print(f"[CDP] Connected to: {ws_url}", flush=True)

    async with websockets.connect(ws_url) as ws:
        msg_id = 1
        await send_cmd(ws, msg_id, "Runtime.enable"); msg_id += 1
        await send_cmd(ws, msg_id, "Page.enable"); msg_id += 1

        # Track console errors
        await eval_js(ws, msg_id, """
            (() => {
                window.__audit_console_errors = [];
                const orig = console.error;
                console.error = function(...args) {
                    window.__audit_console_errors.push(args.map(a => String(a)).join(' '));
                    orig.apply(console, args);
                };
            })()
        """); msg_id += 1

        # 1. Login as Manager (or Owner)
        print("\n--- 1. AUTHENTICATION & NAVIGATION TO #REPORTS ---", flush=True)
        login_res = await eval_js(ws, msg_id, """
            (async () => {
                localStorage.removeItem('sims_token');
                localStorage.removeItem('sims_access_token');
                localStorage.removeItem('sims_user');
                await Auth.login('demo_manager', 'password123');
                App.setupSidebar();
                App.navigate('reports');
                return { success: Auth.isAuthenticated(), role: Auth.getUser()?.role, hash: window.location.hash };
            })()
        """); msg_id += 1
        print(f"Login & Navigation: {login_res}", flush=True)

        await asyncio.sleep(1.5)

        # 2. Inspect DOM of Reports page
        print("\n--- 2. DOM STRUCTURE INSPECTION ---", flush=True)
        dom_info = await eval_js(ws, msg_id, """
            (() => {
                const content = document.getElementById('content-area');
                const page = content?.querySelector('.page.active');
                const actionsBar = content?.querySelector('.actions-bar');
                const statusBadge = document.getElementById('inventory-status');
                const exportBtn = document.getElementById('btn-export-csv');
                const generateBtn = document.getElementById('btn-generate-report');
                const table = document.getElementById('reports-table');
                const ths = table ? Array.from(table.querySelectorAll('th')).map(th => th.innerText.trim()) : [];
                const rows = table ? Array.from(table.querySelectorAll('tbody tr')).map(tr => {
                    return Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
                }) : [];

                return {
                    pageExists: !!page,
                    actionsBarText: actionsBar?.innerText,
                    statusBadgeText: statusBadge?.innerText,
                    hasExportBtn: !!exportBtn,
                    exportBtnText: exportBtn?.innerText,
                    hasGenerateBtn: !!generateBtn,
                    generateBtnText: generateBtn?.innerText,
                    tableExists: !!table,
                    tableHeaders: ths,
                    rowCount: rows.length,
                    sampleRows: rows.slice(0, 5)
                };
            })()
        """); msg_id += 1
        print(f"DOM Info:\n{json.dumps(dom_info, indent=2)}", flush=True)

        # 3. Check what controls are MISSING vs audit requirements
        print("\n--- 3. FEATURE & CONTROLS GAP ANALYSIS ---", flush=True)
        gaps = await eval_js(ws, msg_id, """
            (() => {
                const c = document.getElementById('content-area');
                return {
                    hasDateRangePicker: !!c.querySelector('input[type="date"], .date-range, #date-range'),
                    hasReportTypeSelector: !!c.querySelector('select, .report-type, .tabs, .nav-tabs'),
                    hasReportCards: !!c.querySelector('.report-card, .card, .grid'),
                    hasSearchBox: !!c.querySelector('input[type="search"], input[placeholder*="Search"]'),
                    hasPagination: !!c.querySelector('.pagination, .pager'),
                    hasSorting: !!c.querySelector('th.sortable, th[data-sort]'),
                    hasExcelExport: !!c.querySelector('#btn-export-excel, .btn-excel'),
                    hasPdfExport: !!c.querySelector('#btn-export-pdf, .btn-pdf'),
                    hasDetailView: !!c.querySelector('.btn-view, tr[data-report-id]'),
                    tableHasTotalRow: !!c.querySelector('tfoot, tr.total-row')
                };
            })()
        """); msg_id += 1
        print(f"Controls Gaps:\n{json.dumps(gaps, indent=2)}", flush=True)

        # 4. Test Export CSV Click
        print("\n--- 4. TEST EXPORT CSV BUTTON CLICK ---", flush=True)
        toast_before = await eval_js(ws, msg_id, "document.getElementById('toast-container')?.innerText"); msg_id += 1
        await eval_js(ws, msg_id, "document.getElementById('btn-export-csv').click();"); msg_id += 1
        await asyncio.sleep(1.5)
        toast_after = await eval_js(ws, msg_id, "document.getElementById('toast-container')?.innerText"); msg_id += 1
        print(f"Toast after Export CSV click: '{toast_after}'", flush=True)

        # 5. Test Access by Employee and Supplier (RBAC checks)
        print("\n--- 5. RBAC ACCESS TEST (EMPLOYEE & SUPPLIER) ---", flush=True)
        emp_nav = await eval_js(ws, msg_id, """
            (async () => {
                localStorage.removeItem('sims_token');
                localStorage.removeItem('sims_access_token');
                localStorage.removeItem('sims_user');
                await Auth.login('demo_employee', 'password123');
                App.setupSidebar();
                App.navigate('reports');
                return {
                    role: Auth.getUser()?.role,
                    hash: window.location.hash,
                    sidebarHasReports: !!document.querySelector('.nav-item[data-path="reports"]')
                };
            })()
        """); msg_id += 1
        print(f"Employee Navigation to Reports: {emp_nav}", flush=True)

        sup_nav = await eval_js(ws, msg_id, """
            (async () => {
                localStorage.removeItem('sims_token');
                localStorage.removeItem('sims_access_token');
                localStorage.removeItem('sims_user');
                await Auth.login('demo_supplier', 'password123');
                App.setupSidebar();
                App.navigate('reports');
                return {
                    role: Auth.getUser()?.role,
                    hash: window.location.hash,
                    sidebarHasReports: !!document.querySelector('.nav-item[data-path="reports"]')
                };
            })()
        """); msg_id += 1
        print(f"Supplier Navigation to Reports: {sup_nav}", flush=True)

        # 6. Check console errors
        console_errors = await eval_js(ws, msg_id, "window.__audit_console_errors || []"); msg_id += 1
        print(f"\n--- 6. CONSOLE ERRORS ---: count={len(console_errors)}")
        for err in console_errors:
            print(f"  Console Error: {err}")

        # Return session to demo_manager
        await eval_js(ws, msg_id, """
            (async () => {
                localStorage.removeItem('sims_token');
                localStorage.removeItem('sims_access_token');
                localStorage.removeItem('sims_user');
                await Auth.login('demo_manager', 'password123');
                App.setupSidebar();
                App.navigate('reports');
            })()
        """); msg_id += 1

if __name__ == '__main__':
    asyncio.run(main())
