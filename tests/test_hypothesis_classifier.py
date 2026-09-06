from hypothesis_classifier import case_features, classify_case_holdout, train_classifier


def _event(event_id, case_id, **overrides):
    base = {
        "event_id": event_id, "case_id": case_id, "timestamp": "2026-01-15 08:00:00",
        "event_type": "login_success", "user": "u", "device": "d",
        "source_ip": "10.0.0.15", "destination": "x", "process": "explorer.exe",
        "severity": "low", "source": "auth_log", "label": "benign",
        "description": "normal activity",
    }
    base.update(overrides)
    return base


def test_case_features_returns_expected_keys():
    events = [_event("E1", "C1"), _event("E2", "C1", severity="high")]
    features = case_features(events)
    assert "n_events" in features
    assert features["n_events"] == 2
    assert 0.0 <= features["frac_high_severity"] <= 1.0


def test_holdout_never_trains_on_target_case():
    events_by_case = {
        "C1": [_event("E1", "C1")],
        "C2": [_event("E2", "C2", severity="high")],
        "C3": [_event("E3", "C3")],
    }
    labels_by_case = {"C1": "type_a", "C2": "type_b", "C3": "type_a"}

    probs = classify_case_holdout("C1", events_by_case, labels_by_case)
    # sanity: probabilities sum to ~1 and only cover the OTHER cases' labels
    assert abs(sum(probs.values()) - 1.0) < 1e-6
    assert set(probs.keys()) <= {"type_a", "type_b"}


def test_holdout_raises_without_other_cases():
    events_by_case = {"C1": [_event("E1", "C1")]}
    labels_by_case = {"C1": "type_a"}
    try:
        classify_case_holdout("C1", events_by_case, labels_by_case)
        assert False, "expected ValueError with no other cases to train on"
    except ValueError:
        pass
