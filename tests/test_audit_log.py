import json
import os
import importlib


def test_record_and_read_round_trip(tmp_path, monkeypatch):
    log_path = tmp_path / "audit_log.jsonl"

    import audit_log
    importlib.reload(audit_log)
    monkeypatch.setattr(audit_log, "LOG_PATH", str(log_path))

    entry = audit_log.record_decision(
        case_id="CASE001",
        investigator_name="tester",
        chosen_hypothesis="credential_compromise",
        rationale="test rationale",
        agreed_with_ai=True,
    )
    assert entry["case_id"] == "CASE001"
    assert os.path.exists(log_path)

    entries = audit_log.read_all_decisions()
    assert len(entries) == 1
    assert entries[0]["investigator_name"] == "tester"


def test_log_is_append_only_never_overwrites(tmp_path, monkeypatch):
    log_path = tmp_path / "audit_log.jsonl"
    import audit_log
    importlib.reload(audit_log)
    monkeypatch.setattr(audit_log, "LOG_PATH", str(log_path))

    audit_log.record_decision("CASE001", "a", "credential_compromise", "first", True)
    audit_log.record_decision("CASE002", "b", "legitimate_admin_activity", "second", False)

    entries = audit_log.read_all_decisions()
    assert len(entries) == 2
    assert entries[0]["case_id"] == "CASE001"
    assert entries[1]["case_id"] == "CASE002"


def test_missing_log_file_returns_empty_list(tmp_path, monkeypatch):
    import audit_log
    importlib.reload(audit_log)
    monkeypatch.setattr(audit_log, "LOG_PATH", str(tmp_path / "does_not_exist.jsonl"))
    assert audit_log.read_all_decisions() == []


# ---------------------------------------------------------------------------
# Hash chain integrity
# ---------------------------------------------------------------------------

def _fresh_audit_log(tmp_path, monkeypatch):
    log_path = tmp_path / "audit_log.jsonl"
    import audit_log
    importlib.reload(audit_log)
    monkeypatch.setattr(audit_log, "LOG_PATH", str(log_path))
    return audit_log


def test_first_entry_chains_from_the_genesis_hash(tmp_path, monkeypatch):
    audit_log = _fresh_audit_log(tmp_path, monkeypatch)
    entry = audit_log.record_decision("CASE001", "a", "credential_compromise", "first", True)
    assert entry["prev_hash"] == audit_log.GENESIS_HASH
    assert entry["entry_hash"] and entry["entry_hash"] != audit_log.GENESIS_HASH


def test_each_entry_chains_to_the_previous_entrys_hash(tmp_path, monkeypatch):
    audit_log = _fresh_audit_log(tmp_path, monkeypatch)
    first = audit_log.record_decision("CASE001", "a", "credential_compromise", "first", True)
    second = audit_log.record_decision("CASE002", "b", "legitimate_admin_activity", "second", False)
    assert second["prev_hash"] == first["entry_hash"]


def test_verify_chain_is_valid_on_an_untouched_log(tmp_path, monkeypatch):
    audit_log = _fresh_audit_log(tmp_path, monkeypatch)
    audit_log.record_decision("CASE001", "a", "credential_compromise", "first", True)
    audit_log.record_decision("CASE002", "b", "legitimate_admin_activity", "second", False)
    report = audit_log.verify_chain()
    assert report["valid"] is True
    assert report["checked"] == 2
    assert report["legacy_entries"] == 0
    assert report["broken_at_line"] is None


def test_verify_chain_on_empty_log_is_trivially_valid(tmp_path, monkeypatch):
    audit_log = _fresh_audit_log(tmp_path, monkeypatch)
    report = audit_log.verify_chain()
    assert report == {"valid": True, "checked": 0, "legacy_entries": 0,
                       "broken_at_line": None, "reason": None}


def test_verify_chain_detects_an_edited_field(tmp_path, monkeypatch):
    audit_log = _fresh_audit_log(tmp_path, monkeypatch)
    audit_log.record_decision("CASE001", "a", "credential_compromise", "first", True)
    audit_log.record_decision("CASE002", "b", "legitimate_admin_activity", "second", False)

    # Tamper with the first entry's rationale directly on disk, exactly
    # the scenario hash chaining exists to catch (see audit_log.py's
    # module docstring: append-only code doesn't stop file edits).
    lines = audit_log.read_all_decisions()
    lines[0]["rationale"] = "an attacker rewrote this after the fact"
    with open(audit_log.LOG_PATH, "w", encoding="utf-8") as f:
        for entry in lines:
            f.write(json.dumps(entry) + "\n")

    report = audit_log.verify_chain()
    assert report["valid"] is False
    assert report["broken_at_line"] == 0
    assert "content no longer matches" in report["reason"]


def test_verify_chain_detects_a_deleted_entry(tmp_path, monkeypatch):
    audit_log = _fresh_audit_log(tmp_path, monkeypatch)
    audit_log.record_decision("CASE001", "a", "credential_compromise", "first", True)
    audit_log.record_decision("CASE002", "b", "legitimate_admin_activity", "second", False)
    audit_log.record_decision("CASE003", "c", "insider_data_exfiltration", "third", True)

    # Remove the middle entry entirely - the third entry's prev_hash now
    # points at a hash that no longer appears anywhere in the file.
    lines = audit_log.read_all_decisions()
    del lines[1]
    with open(audit_log.LOG_PATH, "w", encoding="utf-8") as f:
        for entry in lines:
            f.write(json.dumps(entry) + "\n")

    report = audit_log.verify_chain()
    assert report["valid"] is False
    assert report["broken_at_line"] == 1
    assert "prev_hash" in report["reason"]


def test_legacy_entries_without_a_hash_are_not_reported_as_tampered(tmp_path, monkeypatch):
    """
    A log written before hash chaining existed has no entry_hash key at
    all. verify_chain() must treat that as "can't verify this old row,"
    not "the chain is broken" - otherwise upgrading this feature would
    make every pre-existing audit log look tampered.
    """
    audit_log = _fresh_audit_log(tmp_path, monkeypatch)
    legacy_entry = {
        "timestamp": "2026-01-01T00:00:00+00:00", "case_id": "CASE001",
        "investigator_name": "old_user", "chosen_hypothesis": "credential_compromise",
        "rationale": "written before hash chaining existed", "agreed_with_ai": True,
        "study_group": None, "time_to_decision_seconds": None,
    }
    with open(audit_log.LOG_PATH, "w", encoding="utf-8") as f:
        f.write(json.dumps(legacy_entry) + "\n")

    # New entries recorded after the upgrade should still chain cleanly,
    # starting from the genesis hash (there's no entry_hash before them).
    entry = audit_log.record_decision("CASE002", "new_user", "legitimate_admin_activity", "post-upgrade", False)
    assert entry["prev_hash"] == audit_log.GENESIS_HASH

    report = audit_log.verify_chain()
    assert report["valid"] is True
    assert report["legacy_entries"] == 1
    assert report["checked"] == 1
