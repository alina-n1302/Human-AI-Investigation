from baseline import score_event, rank_events


def _event(**overrides):
    base = {
        "event_id": "T1", "case_id": "TEST", "timestamp": "2026-01-15 08:00:00",
        "event_type": "login_success", "user": "u", "device": "d",
        "source_ip": "10.0.0.15", "destination": "x", "process": "explorer.exe",
        "severity": "low", "source": "auth_log", "label": "benign",
        "description": "normal daytime activity",
    }
    base.update(overrides)
    return base


def test_unusual_hour_adds_points():
    daytime_score, _ = score_event(_event(timestamp="2026-01-15 14:00:00"))
    night_score, reasons = score_event(_event(timestamp="2026-01-15 02:00:00"))
    assert night_score > daytime_score
    assert any("unusual hour" in r for r in reasons)


def test_unknown_ip_adds_points():
    known_score, _ = score_event(_event(source_ip="10.0.0.15"))
    unknown_score, reasons = score_event(_event(source_ip="1.2.3.4"))
    assert unknown_score > known_score
    assert any("not on the known office IP list" in r for r in reasons)


def test_malicious_destination_is_heavily_weighted():
    score, reasons = score_event(_event(destination="malicious-c2.example"))
    assert score >= 4
    assert any("known-bad domain" in r for r in reasons)


def test_rank_events_sorts_descending():
    events = [
        _event(event_id="LOW", timestamp="2026-01-15 14:00:00"),
        _event(event_id="HIGH", timestamp="2026-01-15 02:00:00", source_ip="1.2.3.4",
               destination="malicious-c2.example"),
    ]
    ranked = rank_events(events)
    assert ranked[0]["event_id"] == "HIGH"
    assert ranked[0]["baseline_score"] >= ranked[1]["baseline_score"]
