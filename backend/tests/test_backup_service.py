import pytest

from app.services.team3 import backup_service


@pytest.fixture
def valid_backup():
    payload = {"backup_info": {"backup_type": "full", "version": "1.0"}}
    for table, primary_key in backup_service.RESTORE_TABLES:
        payload[table] = [{primary_key: 1}]
    return payload


def test_validate_backup_and_restore_plan(valid_backup):
    assert backup_service.validate_backup(valid_backup)["valid"]
    plan = backup_service.prepare_restore(valid_backup)
    assert plan["dry_run"] is True
    assert len(plan["restore_order"]) == 14
    assert "BackupHistory" not in valid_backup


def test_validation_rejects_missing_tables(valid_backup):
    del valid_backup["Reports"]
    result = backup_service.validate_backup(valid_backup)
    assert not result["valid"]
    assert "Reports" in result["missing_tables"]


def test_validation_rejects_missing_or_duplicate_primary_keys(valid_backup):
    valid_backup["Roles"] = [{"role_id": 1}, {"role_id": 1}]
    assert "Duplicate" in backup_service.validate_backup(valid_backup)["message"]
    valid_backup["Roles"] = [{"role_name": "Manager"}]
    assert not backup_service.validate_backup(valid_backup)["valid"]


def test_restore_calls_transactional_rpc(valid_backup, monkeypatch):
    class Response:
        data = [{"table": "Roles", "status": "Success"}]

    class Query:
        def execute(self):
            return Response()

    class Client:
        def rpc(self, name, params):
            assert name == "restore_application_backup"
            assert params["p_backup"] is valid_backup
            return Query()

    monkeypatch.setattr(backup_service, "supabase", Client())
    assert backup_service.restore_backup(valid_backup)["valid"]


def test_restore_failure_is_sanitized(valid_backup, monkeypatch):
    class Client:
        def rpc(self, *_args, **_kwargs):
            raise RuntimeError("database secret detail")

    monkeypatch.setattr(backup_service, "supabase", Client())
    result = backup_service.restore_backup(valid_backup)
    assert not result["valid"]
    assert "database secret detail" not in str(result)


def test_backup_table_reads_are_paginated(monkeypatch):
    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    offsets = []

    class Response:
        def __init__(self, data):
            self.data = data

    class Query:
        def range(self, start, end):
            offsets.append((start, end))
            self.start = start
            self.end = end
            return self

        def execute(self):
            return Response(rows[self.start:self.end + 1])

    class Client:
        def table(self, _table):
            return self

        def select(self, _columns):
            return Query()

    monkeypatch.setattr(backup_service, "supabase", Client())
    monkeypatch.setattr(backup_service, "BACKUP_PAGE_SIZE", 2)
    assert backup_service._read_all_rows("Products") == rows
    assert offsets == [(0, 1), (2, 3)]
