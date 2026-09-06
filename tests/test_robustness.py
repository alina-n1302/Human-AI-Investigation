from robustness import (
    apply_perturbation, top_k_overlap, conclusion_flip, summarize, PERTURBATIONS,
)


def _events(n=10):
    return [
        {
            "event_id": f"E{i}", "case_id": "TEST", "timestamp": f"2026-01-15 0{i % 6}:00:00",
            "event_type": "login_success", "user": "u", "device": "d",
            "source_ip": f"10.0.0.{i}", "destination": "x", "process": "explorer.exe",
            "severity": "low", "source": "auth_log", "label": "benign",
            "description": "normal activity",
        }
        for i in range(n)
    ]


def test_incomplete_removes_a_fraction_not_a_fixed_count():
    events = _events(20)
    damaged_10pct = apply_perturbation(events, "incomplete_10pct")
    damaged_40pct = apply_perturbation(events, "incomplete_40pct")
    assert len(damaged_10pct) < len(events)
    assert len(damaged_40pct) < len(damaged_10pct)


def test_incomplete_never_empties_the_case():
    events = _events(2)
    damaged = apply_perturbation(events, "incomplete_40pct")
    assert len(damaged) >= 1


def test_noisy_levels_add_different_amounts():
    events = _events(5)
    one_x = apply_perturbation(events, "noisy_1x")
    three_x = apply_perturbation(events, "noisy_3x")
    assert len(one_x) == len(events) + 1
    assert len(three_x) == len(events) + 3


def test_obfuscated_changes_some_but_not_necessarily_all_ips():
    events = _events(10)
    damaged = apply_perturbation(events, "obfuscated_25pct")
    original_ips = {e["source_ip"] for e in events}
    damaged_ips = {e["source_ip"] for e in damaged}
    assert damaged_ips != original_ips


def test_delayed_shifts_timestamp_forward():
    events = _events(3)
    damaged = apply_perturbation(events, "delayed_3h")
    # at least one event's timestamp should differ from the original
    originals = {e["event_id"]: e["timestamp"] for e in events}
    changed = [e for e in damaged if e["timestamp"] != originals[e["event_id"]]]
    assert len(changed) == 1


def test_top_k_overlap_identical_lists_is_1():
    a = [{"event_id": "X"}, {"event_id": "Y"}, {"event_id": "Z"}]
    assert top_k_overlap(a, a, k=3) == 1.0


def test_top_k_overlap_disjoint_lists_is_0():
    a = [{"event_id": "X"}, {"event_id": "Y"}]
    b = [{"event_id": "P"}, {"event_id": "Q"}]
    assert top_k_overlap(a, b, k=2) == 0.0


def test_conclusion_flip_detects_change():
    clean = {"leading_hypothesis": "credential_compromise"}
    same = {"leading_hypothesis": "credential_compromise"}
    different = {"leading_hypothesis": "legitimate_admin_activity"}
    assert conclusion_flip(clean, same) is False
    assert conclusion_flip(clean, different) is True


def test_summarize_computes_mean_and_flip_rate():
    report = {
        "a": {"top3_evidence_overlap": 1.0, "conclusion_flipped": False},
        "b": {"top3_evidence_overlap": 0.0, "conclusion_flipped": True},
    }
    summary = summarize(report)
    assert summary["mean_top3_overlap"] == 0.5
    assert summary["flip_rate"] == 0.5


def test_perturbation_registry_has_multiple_severity_levels():
    """Guards against regressing back to one fixed-severity perturbation per family."""
    incomplete_levels = [k for k in PERTURBATIONS if k.startswith("incomplete_")]
    assert len(incomplete_levels) >= 3
