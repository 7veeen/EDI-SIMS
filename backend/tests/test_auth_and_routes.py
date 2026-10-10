from datetime import datetime, timedelta, timezone

import jwt
import pytest

from main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-secret-that-is-at-least-32-bytes")
    app.config.update(TESTING=True)
    return app.test_client()


def token(role="Manager", subject="2", expired=False):
    expiry = datetime.now(timezone.utc) - timedelta(seconds=1) if expired else datetime.now(timezone.utc) + timedelta(minutes=5)
    return jwt.encode({"sub": subject, "role": role, "exp": expiry}, "unit-test-secret-that-is-at-least-32-bytes", algorithm="HS256")


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer not-a-token"}])
def test_backup_routes_reject_missing_or_invalid_jwt(client, headers):
    assert client.get("/api/backups", headers=headers).status_code == 401


def test_expired_jwt_is_rejected(client):
    response = client.get("/api/backups", headers={"Authorization": f"Bearer {token(expired=True)}"})
    assert response.status_code == 401
    assert "expired" in response.json["error"]


def test_jwt_with_wrong_signature_is_rejected(client):
    forged = jwt.encode({"sub": "2", "role": "Owner",
                         "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                        "attacker-controlled-signing-key-value", algorithm="HS256")
    response = client.get("/api/backups", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_invalid_subject_is_rejected(client):
    response = client.get("/api/backups", headers={"Authorization": f"Bearer {token(subject='user-2')}"})
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["Employee", "Supplier"])
@pytest.mark.parametrize("method, path", [("post", "/api/backups/9/restore"), ("delete", "/api/backups/9")])
def test_employee_and_supplier_cannot_restore_or_delete(client, role, method, path):
    response = getattr(client, method)(path, json={"dry_run": True},
                                       headers={"Authorization": f"Bearer {token(role=role)}"})
    assert response.status_code == 403


@pytest.mark.parametrize("role", ["Owner", "Manager"])
def test_restore_dry_run_does_not_call_restore_rpc(client, monkeypatch, role):
    import app.routes.team3.backup_routes as routes

    payload = {"backup_info": {"backup_type": "full", "version": "1.0"}}
    for table, pk in routes.backups.RESTORE_TABLES:
        payload[table] = [{pk: 1}]
    monkeypatch.setattr(routes.backups, "download_backup", lambda _id: ({"backup_name": "b.json"}, __import__("json").dumps(payload).encode()))
    monkeypatch.setattr(routes.backups, "restore_backup", lambda _backup: pytest.fail("dry run must not restore"))
    response = client.post("/api/backups/9/restore", json={"dry_run": True},
                           headers={"Authorization": f"Bearer {token(role=role)}"})
    assert response.status_code == 200
    assert response.json["dry_run"] is True


def test_required_backup_routes_are_registered(client):
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert {"/api/backups", "/api/backups/<int:backup_id>",
            "/api/backups/<int:backup_id>/download", "/api/backups/<int:backup_id>/restore"} <= rules


@pytest.mark.parametrize("origin", ["http://127.0.0.1:5500", "http://localhost:5500"])
def test_backup_cors_preflight_allows_frontend_origins(client, origin):
    response = client.options("/api/backups", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == origin
    assert "authorization" in response.headers["Access-Control-Allow-Headers"].lower()
    assert "content-type" in response.headers["Access-Control-Allow-Headers"].lower()


def test_backup_cors_rejects_unlisted_origin(client):
    response = client.options("/api/backups", headers={
        "Origin": "http://evil.example",
        "Access-Control-Request-Method": "GET",
    })
    assert "Access-Control-Allow-Origin" not in response.headers


def test_backup_get_works_with_cors_and_valid_jwt(client, monkeypatch):
    import app.routes.team3.backup_routes as routes

    monkeypatch.setattr(routes.backups, "list_backups", lambda: [])
    response = client.get("/api/backups", headers={
        "Origin": "http://127.0.0.1:5500",
        "Authorization": f"Bearer {token()}",
    })
    assert response.status_code == 200
    assert response.json["backups"] == []
    assert response.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5500"


def test_create_backup_uses_authenticated_user(client, monkeypatch):
    import app.routes.team3.backup_routes as routes

    monkeypatch.setattr(routes.backups, "create_backup", lambda created_by: {"created_by": created_by})
    response = client.post("/api/backups", headers={"Authorization": f"Bearer {token(subject='42')}"})
    assert response.status_code == 201
    assert response.json["backup"]["created_by"] == 42


def test_backup_history_single_download_and_delete(client, monkeypatch):
    import app.routes.team3.backup_routes as routes

    metadata = {"backup_id": 7, "backup_name": "backup.json"}
    monkeypatch.setattr(routes.backups, "list_backups", lambda: [metadata])
    monkeypatch.setattr(routes.backups, "get_backup", lambda _id: metadata)
    monkeypatch.setattr(routes.backups, "download_backup", lambda _id: (metadata, b"{}"))
    monkeypatch.setattr(routes.backups, "delete_backup", lambda _id: metadata)
    auth = {"Authorization": f"Bearer {token()}"}

    assert client.get("/api/backups", headers=auth).json["backups"] == [metadata]
    assert client.get("/api/backups/7", headers=auth).json["backup"] == metadata
    assert client.get("/api/backups/7/download", headers=auth).status_code == 200
    assert client.delete("/api/backups/7", headers=auth).status_code == 200


def test_missing_backup_returns_404(client, monkeypatch):
    import app.routes.team3.backup_routes as routes

    def missing(_id):
        raise routes.backups.BackupNotFound()

    monkeypatch.setattr(routes.backups, "get_backup", missing)
    response = client.get("/api/backups/999", headers={"Authorization": f"Bearer {token()}"})
    assert response.status_code == 404


def test_invalid_backup_json_returns_400(client, monkeypatch):
    import app.routes.team3.backup_routes as routes

    monkeypatch.setattr(routes.backups, "download_backup", lambda _id: ({}, b"not json"))
    response = client.post("/api/backups/1/restore", json={"dry_run": True},
                           headers={"Authorization": f"Bearer {token()}"})
    assert response.status_code == 400


def test_download_storage_failure_returns_500(client, monkeypatch):
    import app.routes.team3.backup_routes as routes

    monkeypatch.setattr(routes.backups, "download_backup", lambda _id: (_ for _ in ()).throw(RuntimeError("storage details")))
    response = client.get("/api/backups/1/download", headers={"Authorization": f"Bearer {token()}"})
    assert response.status_code == 500
    assert "storage details" not in response.get_data(as_text=True)


def test_owner_can_delete_backup(client, monkeypatch):
    import app.routes.team3.backup_routes as routes

    monkeypatch.setattr(routes.backups, "delete_backup", lambda _id: {})
    response = client.delete("/api/backups/1", headers={"Authorization": f"Bearer {token(role='Owner')}"})
    assert response.status_code == 200
