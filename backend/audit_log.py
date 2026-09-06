import hashlib
import json
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "results", "audit_log.jsonl")


GENESIS_HASH = "0" * 64


def _canonical(fields):
    return json.dumps(fields, sort_keys=True, separators=(",", ":"))


def _compute_hash(prev_hash, fields):
    payload = prev_hash + _canonical(fields)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _last_hash():
    if not os.path.exists(LOG_PATH):
        return GENESIS_HASH
    last_line = None
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last_line = line
    if last_line is None:
        return GENESIS_HASH
    return json.loads(last_line).get("entry_hash", GENESIS_HASH)


def record_decision(
    case_id,
    investigator_name,
    chosen_hypothesis,
    rationale,
    agreed_with_ai=None,
    study_group=None,
    time_to_decision_seconds=None,
):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    fields = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "investigator_name": investigator_name,
        "chosen_hypothesis": chosen_hypothesis,
        "rationale": rationale,
        "agreed_with_ai": agreed_with_ai,
        "study_group": study_group,
        "time_to_decision_seconds": time_to_decision_seconds,
    }
    prev_hash = _last_hash()
    entry = {
        **fields,
        "prev_hash": prev_hash,
        "entry_hash": _compute_hash(prev_hash, fields),
    }

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_all_decisions():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def verify_chain():
    entries = read_all_decisions()
    legacy_entries = 0
    checked = 0
    expected_prev = GENESIS_HASH

    for i, entry in enumerate(entries):
        if "entry_hash" not in entry:
            legacy_entries += 1
            continue

        if entry.get("prev_hash") != expected_prev:
            return {
                "valid": False,
                "checked": checked,
                "legacy_entries": legacy_entries,
                "broken_at_line": i,
                "reason": "this entry's prev_hash does not match the hash of the entry "
                "before it - a line was edited, reordered, or removed",
            }

        fields = {
            k: v for k, v in entry.items() if k not in ("prev_hash", "entry_hash")
        }
        recomputed = _compute_hash(expected_prev, fields)
        if recomputed != entry["entry_hash"]:
            return {
                "valid": False,
                "checked": checked,
                "legacy_entries": legacy_entries,
                "broken_at_line": i,
                "reason": "this entry's own content no longer matches its recorded hash - "
                "it was edited after being written",
            }

        checked += 1
        expected_prev = entry["entry_hash"]

    return {
        "valid": True,
        "checked": checked,
        "legacy_entries": legacy_entries,
        "broken_at_line": None,
        "reason": None,
    }


if __name__ == "__main__":
    record_decision(
        case_id="CASE001",
        investigator_name="demo_user",
        chosen_hypothesis="credential_compromise",
        rationale="Foreign IP, malware domain, no maintenance ticket - matches AI's leading hypothesis.",
        agreed_with_ai=True,
    )
    for entry in read_all_decisions():
        print(entry)
    print("Chain check:", verify_chain())

    print("\nSimulating tampering (editing a rationale in place on disk)...")
    with open(LOG_PATH, encoding="utf-8") as f:
        lines = f.readlines()
    tampered = json.loads(lines[0])
    tampered["rationale"] = "tampered rationale"
    lines[0] = json.dumps(tampered) + "\n"
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Chain check after tampering:", verify_chain())
