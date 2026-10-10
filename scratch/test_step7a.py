import sys
import os
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def log(msg):
    print(msg, flush=True)

def get_token(username, password="password123"):
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password})
    if res.status_code == 200:
        data = res.json()
        return data.get("access_token") or data.get("token")
    log(f"Login failed for {username}: {res.status_code} {res.text}")
    return None

def main():
    log("==================================================")
    log("STEP 7A — NOTIFICATION FOUNDATION & SECURITY TESTS")
    log("==================================================")

    # 0. Obtain JWT tokens for diverse roles
    owner_token = get_token("demo_owner")
    manager_token = get_token("demo_manager")
    employee_token = get_token("demo_employee")
    supplier_token = get_token("demo_supplier")

    # If demo accounts not present, fallback
    if not owner_token: owner_token = get_token("owner")
    if not manager_token: manager_token = get_token("manager1")
    if not employee_token: employee_token = get_token("employee1")
    if not supplier_token: supplier_token = get_token("supplier1")

    assert owner_token, "Owner token failed"
    assert manager_token, "Manager token failed"
    assert employee_token, "Employee token failed"
    assert supplier_token, "Supplier token failed"
    log("[INIT] Logged in as Owner, Manager, Employee, Supplier successfully.\n")

    passed_count = 0
    total_count = 20

    # ==================================================
    # AUTHENTICATION TESTS (TC-01 - TC-04)
    # ==================================================
    log("--- [SECTION 1] AUTHENTICATION TESTS ---")
    
    # TC-01: Anonymous GET /api/notifications/
    r = requests.get(f"{BASE_URL}/api/notifications/")
    assert r.status_code == 401, f"TC-01 Failed: expected 401, got {r.status_code}"
    log(f"[PASS] TC-01: Anonymous GET /api/notifications/ -> {r.status_code}")
    passed_count += 1

    # TC-02: Anonymous PATCH /api/notifications/<id>/read
    r = requests.patch(f"{BASE_URL}/api/notifications/999999/read")
    assert r.status_code == 401, f"TC-02 Failed: expected 401, got {r.status_code}"
    log(f"[PASS] TC-02: Anonymous PATCH /api/notifications/999999/read -> {r.status_code}")
    passed_count += 1

    # TC-03: Anonymous GET /api/notifications/unread-count
    r = requests.get(f"{BASE_URL}/api/notifications/unread-count")
    assert r.status_code == 401, f"TC-03 Failed: expected 401, got {r.status_code}"
    log(f"[PASS] TC-03: Anonymous GET /api/notifications/unread-count -> {r.status_code}")
    passed_count += 1

    # TC-04: Anonymous PATCH /api/notifications/read-all
    r = requests.patch(f"{BASE_URL}/api/notifications/read-all")
    assert r.status_code == 401, f"TC-04 Failed: expected 401, got {r.status_code}"
    log(f"[PASS] TC-04: Anonymous PATCH /api/notifications/read-all -> {r.status_code}\n")
    passed_count += 1

    # ==================================================
    # SETUP TEST NOTIFICATIONS VIA SERVICE
    # ==================================================
    # Import service in backend context to create clean test records for each user
    sys.path.insert(0, os.path.abspath("backend"))
    from app.services.team3.notification_service import create_notification
    import jwt

    # Decode tokens to get exact user_ids
    emp_uid = jwt.decode(employee_token, options={"verify_signature": False})["sub"]
    mgr_uid = jwt.decode(manager_token, options={"verify_signature": False})["sub"]
    own_uid = jwt.decode(owner_token, options={"verify_signature": False})["sub"]
    sup_uid = jwt.decode(supplier_token, options={"verify_signature": False})["sub"]

    log(f"[INFO] UIDs: Employee={emp_uid}, Manager={mgr_uid}, Owner={own_uid}, Supplier={sup_uid}")

    # Seed fresh test notifications with unique references
    import time
    ts = int(time.time())

    emp_notif_1, err, _ = create_notification(
        user_id=emp_uid,
        title=f"Employee Test Alert {ts}",
        message="Employee operational task pending.",
        notification_type="Task",
        priority="Normal",
        reference_type="TestTask",
        reference_id=ts + 1
    )
    assert emp_notif_1, f"Failed to seed emp notif: {err}"
    emp_nid_1 = emp_notif_1["notification_id"]

    mgr_notif_1, err, _ = create_notification(
        user_id=mgr_uid,
        title=f"Manager Approval Alert {ts}",
        message="PO approval pending review.",
        notification_type="Approval",
        priority="High",
        reference_type="TestPO",
        reference_id=ts + 2
    )
    assert mgr_notif_1, f"Failed to seed mgr notif: {err}"
    mgr_nid_1 = mgr_notif_1["notification_id"]

    # ==================================================
    # USER ISOLATION TESTS (TC-05 - TC-09)
    # ==================================================
    log("--- [SECTION 2] USER ISOLATION TESTS ---")

    # TC-05: Employee A GET notifications -> only Employee A notifications
    headers_emp = {"Authorization": f"Bearer {employee_token}"}
    r = requests.get(f"{BASE_URL}/api/notifications/", headers=headers_emp)
    assert r.status_code == 200, f"TC-05 Failed: {r.status_code} {r.text}"
    emp_list = r.json()
    assert all(n["user_id"] == int(emp_uid) for n in emp_list), "TC-05 Failed: foreign user_id found in list!"
    log(f"[PASS] TC-05: Employee GET notifications -> {len(emp_list)} items, strictly user_id={emp_uid}")
    passed_count += 1

    # TC-06: Employee A attempts to retrieve Manager notification (mgr_nid_1)
    r = requests.get(f"{BASE_URL}/api/notifications/{mgr_nid_1}", headers=headers_emp)
    assert r.status_code in (403, 404), f"TC-06 Failed: expected 403 or 404, got {r.status_code}"
    log(f"[PASS] TC-06: Employee GET Manager notification {mgr_nid_1} -> {r.status_code} (Blocked)")
    passed_count += 1

    # TC-07: Employee A attempts to mark Manager notification as read
    r = requests.patch(f"{BASE_URL}/api/notifications/{mgr_nid_1}/read", headers=headers_emp)
    assert r.status_code in (403, 404), f"TC-07 Failed: expected 403 or 404, got {r.status_code}"
    log(f"[PASS] TC-07: Employee PATCH Manager notification {mgr_nid_1}/read -> {r.status_code} (Blocked)")
    passed_count += 1

    # TC-08: Supplier attempts to access Manager notification
    headers_sup = {"Authorization": f"Bearer {supplier_token}"}
    r = requests.get(f"{BASE_URL}/api/notifications/{mgr_nid_1}", headers=headers_sup)
    assert r.status_code in (403, 404), f"TC-08 Failed: expected 403 or 404, got {r.status_code}"
    log(f"[PASS] TC-08: Supplier GET Manager notification {mgr_nid_1} -> {r.status_code} (Blocked)")
    passed_count += 1

    # TC-09: Owner attempts to access Manager notification (Owner has no personal right to Manager's private alert)
    headers_own = {"Authorization": f"Bearer {owner_token}"}
    r = requests.get(f"{BASE_URL}/api/notifications/{mgr_nid_1}", headers=headers_own)
    assert r.status_code in (403, 404), f"TC-09 Failed: expected 403 or 404, got {r.status_code}"
    log(f"[PASS] TC-09: Owner GET Manager notification {mgr_nid_1} -> {r.status_code} (Blocked - Strict User Isolation)\n")
    passed_count += 1

    # ==================================================
    # READ STATUS TESTS (TC-10 - TC-13)
    # ==================================================
    log("--- [SECTION 3] READ STATUS TESTS ---")

    # TC-10: Mark own unread notification as read
    r = requests.patch(f"{BASE_URL}/api/notifications/{emp_nid_1}/read", headers=headers_emp)
    assert r.status_code == 200, f"TC-10 Failed: {r.status_code} {r.text}"
    read_data = r.json()
    assert read_data.get("is_read") is True, f"TC-10 Failed: is_read is not True: {read_data}"
    assert read_data.get("read_at") is not None, f"TC-10 Failed: read_at is null: {read_data}"
    log(f"[PASS] TC-10: Mark own notification read -> is_read=True, read_at={read_data.get('read_at')}")
    passed_count += 1

    # TC-11: Mark already-read notification again (idempotent)
    r2 = requests.patch(f"{BASE_URL}/api/notifications/{emp_nid_1}/read", headers=headers_emp)
    assert r2.status_code == 200, f"TC-11 Failed: {r2.status_code} {r2.text}"
    r2_data = r2.json()
    assert r2_data.get("is_read") is True, f"TC-11 Failed: is_read should remain True"
    log(f"[PASS] TC-11: Mark already-read notification -> idempotent 200 OK")
    passed_count += 1

    # TC-12: Mark all own notifications as read
    # Seed 2 new unread notifications for Employee
    create_notification(user_id=emp_uid, title=f"Emp Test A {ts}", message="Msg A", reference_type="T1", reference_id=ts+10)
    create_notification(user_id=emp_uid, title=f"Emp Test B {ts}", message="Msg B", reference_type="T2", reference_id=ts+11)
    
    r_all = requests.patch(f"{BASE_URL}/api/notifications/read-all", headers=headers_emp)
    assert r_all.status_code == 200, f"TC-12 Failed: {r_all.status_code} {r_all.text}"
    log(f"[PASS] TC-12: Mark all own notifications as read -> {r_all.json()}")
    passed_count += 1

    # TC-13: Verify another user's unread notifications remain unread
    # Manager notification (mgr_nid_1) should still be unread!
    headers_mgr = {"Authorization": f"Bearer {manager_token}"}
    r_mgr_chk = requests.get(f"{BASE_URL}/api/notifications/{mgr_nid_1}", headers=headers_mgr)
    assert r_mgr_chk.status_code == 200, f"TC-13 Failed: could not read mgr notif: {r_mgr_chk.text}"
    assert r_mgr_chk.json()["is_read"] is False, "TC-13 Failed: Manager's notification was modified by Employee mark-all!"
    log(f"[PASS] TC-13: Manager's unread notification remains is_read=False\n")
    passed_count += 1

    # ==================================================
    # UNREAD COUNT TESTS (TC-14 - TC-16)
    # ==================================================
    log("--- [SECTION 4] UNREAD COUNT TESTS ---")

    # TC-14: Get unread count for manager
    r_uc = requests.get(f"{BASE_URL}/api/notifications/unread-count", headers=headers_mgr)
    assert r_uc.status_code == 200, f"TC-14 Failed: {r_uc.status_code} {r_uc.text}"
    mgr_unread_initial = r_uc.json().get("unread_count")
    assert mgr_unread_initial >= 1, f"TC-14 Failed: expected >= 1, got {mgr_unread_initial}"
    log(f"[PASS] TC-14: Manager unread count retrieved -> {mgr_unread_initial}")
    passed_count += 1

    # TC-15: After marking one notification read, unread count decreases
    r_mk = requests.patch(f"{BASE_URL}/api/notifications/{mgr_nid_1}/read", headers=headers_mgr)
    assert r_mk.status_code == 200
    r_uc2 = requests.get(f"{BASE_URL}/api/notifications/unread-count", headers=headers_mgr)
    mgr_unread_after = r_uc2.json().get("unread_count")
    assert mgr_unread_after == mgr_unread_initial - 1, f"TC-15 Failed: expected {mgr_unread_initial - 1}, got {mgr_unread_after}"
    log(f"[PASS] TC-15: Manager unread count decreased by 1 -> {mgr_unread_after}")
    passed_count += 1

    # TC-16: After mark-all, unread count = 0
    # Seed 1 unread for manager first
    create_notification(user_id=mgr_uid, title=f"Mgr Test {ts}", message="Msg", reference_type="T3", reference_id=ts+20)
    requests.patch(f"{BASE_URL}/api/notifications/read-all", headers=headers_mgr)
    r_uc3 = requests.get(f"{BASE_URL}/api/notifications/unread-count", headers=headers_mgr)
    assert r_uc3.status_code == 200
    assert r_uc3.json().get("unread_count") == 0, f"TC-16 Failed: expected 0, got {r_uc3.json().get('unread_count')}"
    log(f"[PASS] TC-16: Manager unread count after mark-all-as-read -> 0\n")
    passed_count += 1

    # ==================================================
    # SINGLE NOTIFICATION TESTS (TC-17 - TC-18)
    # ==================================================
    log("--- [SECTION 5] SINGLE NOTIFICATION TESTS ---")

    # TC-17: Get own notification -> 200
    r_own = requests.get(f"{BASE_URL}/api/notifications/{emp_nid_1}", headers=headers_emp)
    assert r_own.status_code == 200, f"TC-17 Failed: expected 200, got {r_own.status_code}"
    assert r_own.json()["notification_id"] == emp_nid_1
    log(f"[PASS] TC-17: Get own notification {emp_nid_1} -> 200 OK")
    passed_count += 1

    # TC-18: Get another user's notification -> 403 or 404
    r_other = requests.get(f"{BASE_URL}/api/notifications/{emp_nid_1}", headers=headers_sup)
    assert r_other.status_code in (403, 404), f"TC-18 Failed: expected 403/404, got {r_other.status_code}"
    log(f"[PASS] TC-18: Supplier GET Employee notification {emp_nid_1} -> {r_other.status_code} (IDOR Blocked)\n")
    passed_count += 1

    # ==================================================
    # DUPLICATE NOTIFICATION PREVENTION (TC-19 - TC-20)
    # ==================================================
    log("--- [SECTION 6] DUPLICATE PREVENTION TESTS ---")

    # TC-19: Create same event notification twice
    dup_ref_id = ts + 99
    res1, err1, status1 = create_notification(
        user_id=emp_uid,
        title=f"Duplicate Test {ts}",
        message="Test alert",
        notification_type="Alert",
        priority="High",
        reference_type="DuplicateRef",
        reference_id=dup_ref_id
    )
    assert status1 == 201, f"First notification creation failed: {err1}"
    assert res1["created"] is True

    res2, err2, status2 = create_notification(
        user_id=emp_uid,
        title=f"Duplicate Test {ts}",
        message="Test alert",
        notification_type="Alert",
        priority="High",
        reference_type="DuplicateRef",
        reference_id=dup_ref_id
    )
    assert status2 == 200, f"Second notification call failed: {status2} {err2}"
    assert res2.get("created") is False, "TC-19 Failed: duplicate was inserted!"
    assert res2.get("skipped") is True
    assert res2["notification_id"] == res1["notification_id"]
    log(f"[PASS] TC-19: Duplicate event was prevented! Skipped insert and returned existing ID {res1['notification_id']}")
    passed_count += 1

    # TC-20: Create notifications for two different reference IDs
    res3, err3, status3 = create_notification(
        user_id=emp_uid,
        title=f"Duplicate Test {ts}",
        message="Test alert 2",
        notification_type="Alert",
        priority="High",
        reference_type="DuplicateRef",
        reference_id=dup_ref_id + 1
    )
    assert status3 == 201, f"TC-20 Failed: {err3}"
    assert res3["created"] is True
    assert res3["notification_id"] != res1["notification_id"]
    log(f"[PASS] TC-20: Distinct reference ID successfully created new notification ID {res3['notification_id']}\n")
    passed_count += 1

    # ==================================================
    # ADDITIONAL SECURITY & QUERY INJECTION AUDIT
    # ==================================================
    log("--- [SECTION 7] QUERY TAMPERING & SECURITY AUDIT ---")
    
    # Query parameter tampering: Employee attempts ?user_id=1 to view Owner notifications
    r_tamper = requests.get(f"{BASE_URL}/api/notifications/?user_id={own_uid}", headers=headers_emp)
    assert r_tamper.status_code == 200
    tamper_list = r_tamper.json()
    assert all(n["user_id"] == int(emp_uid) for n in tamper_list), "SECURITY FLAW: Query param user_id bypassed isolation!"
    log(f"[PASS] SEC-01: Query param ?user_id={own_uid} strictly ignored. All returned items belong to emp_uid={emp_uid}")

    # Non-existent notification ID -> 404
    r_nf = requests.get(f"{BASE_URL}/api/notifications/99999999", headers=headers_emp)
    assert r_nf.status_code == 404, f"SEC-02 Failed: expected 404, got {r_nf.status_code}"
    log(f"[PASS] SEC-02: Non-existent notification ID -> 404 Not Found")

    # Invalid Bearer token -> 401
    r_bad_jwt = requests.get(f"{BASE_URL}/api/notifications/", headers={"Authorization": "Bearer invalid.token.value"})
    assert r_bad_jwt.status_code in (401, 422), f"SEC-03 Failed: expected 401/422, got {r_bad_jwt.status_code}"
    log(f"[PASS] SEC-03: Invalid JWT -> {r_bad_jwt.status_code} Unauthorized\n")

    log("==================================================")
    log(f"ALL STEP 7A TESTS PASSED: {passed_count}/{total_count} Standard TCs + 3 Security Tests")
    log("==================================================")

if __name__ == "__main__":
    main()
