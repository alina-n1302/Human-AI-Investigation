from hypotheses import evaluate_case, _matches_any, HYPOTHESES


def _event(event_id, description, **overrides):
    base = {
        "event_id": event_id, "case_id": "TEST", "timestamp": "2026-01-15 08:00:00",
        "event_type": "login_success", "user": "u", "device": "d",
        "source_ip": "10.0.0.15", "destination": "x", "process": "explorer.exe",
        "severity": "low", "source": "auth_log", "label": "benign",
        "description": description,
    }
    base.update(overrides)
    return base


def test_negation_prevents_false_positive():
    """
    'this IP is NOT associated with malware' must NOT count as support
    for credential_compromise - this is the exact bug pattern flagged in
    review (keyword matching with no negation handling).
    """
    keywords = next(h["keywords"] for h in HYPOTHESES if h["id"] == "credential_compromise")
    hits = _matches_any("this ip is not associated with malware", keywords)
    assert "malware" not in hits


def test_plain_positive_mention_still_counts():
    keywords = next(h["keywords"] for h in HYPOTHESES if h["id"] == "credential_compromise")
    hits = _matches_any("a domain known to be associated with malware", keywords)
    assert "malware" in hits


def test_word_boundary_prevents_substring_collision():
    """
    'unusual' must not match inside 'unusually' - the exact false
    positive found while building the insider-exfiltration case.
    """
    keywords = next(h["keywords"] for h in HYPOTHESES if h["id"] == "credential_compromise")
    hits = _matches_any("an unusually large download of files", keywords)
    assert "unusual" not in hits


def test_abstains_when_no_hypothesis_has_support():
    events = [
        _event("E1", "a routine login happened"),
        _event("E2", "a file was opened during work hours"),
    ]
    result = evaluate_case(events)
    assert result["abstain"] is True
    assert result["abstain_reason"] == "insufficient_evidence"
    assert result["leading_hypothesis"] is None


def test_abstains_when_top_two_are_too_close():
    # One keyword hit for compromise, one for legitimate -> tied, both
    # below MIN_SUPPORT_THRESHOLD too, so this should still abstain
    # (insufficient_evidence, since neither individually clears the bar).
    events = [
        _event("E1", "a foreign ip was seen"),
        _event("E2", "a maintenance ticket was referenced"),
    ]
    result = evaluate_case(events)
    assert result["abstain"] is True


def test_clear_evidence_produces_a_leading_hypothesis():
    events = [
        _event("E1", "login from a foreign ip address"),
        _event("E2", "the process contacts a domain known to be associated with malware"),
        _event("E3", "no maintenance window was scheduled"),
    ]
    result = evaluate_case(events)
    assert result["abstain"] is False
    assert result["leading_hypothesis"] == "credential_compromise"


def test_evidence_score_gap_is_not_called_confidence():
    """Guards the terminology fix: the field must be evidence_score_gap, not confidence."""
    events = [_event("E1", "a foreign ip was seen")]
    result = evaluate_case(events)
    assert "evidence_score_gap" in result
    assert "confidence" not in result
