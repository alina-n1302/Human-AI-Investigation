from case_generator import generate_dataset, GENERATORS


def test_generates_expected_number_of_cases():
    events, cases = generate_dataset(cases_per_type=5, seed=1)
    assert len(cases) == 5 * len(GENERATORS)


def test_case_ids_are_unique():
    events, cases = generate_dataset(cases_per_type=10, seed=1)
    ids = [c[0] for c in cases]
    assert len(ids) == len(set(ids))


def test_every_case_has_a_valid_ground_truth():
    events, cases = generate_dataset(cases_per_type=5, seed=1)
    valid = {"credential_compromise", "legitimate_admin_activity",
             "insider_data_exfiltration", "insufficient_evidence"}
    for case in cases:
        assert case[2] in valid


def test_same_seed_is_reproducible():
    events_a, cases_a = generate_dataset(cases_per_type=5, seed=7)
    events_b, cases_b = generate_dataset(cases_per_type=5, seed=7)
    assert events_a == events_b
    assert cases_a == cases_b


def test_different_seeds_produce_different_data():
    events_a, _ = generate_dataset(cases_per_type=5, seed=1)
    events_b, _ = generate_dataset(cases_per_type=5, seed=2)
    assert events_a != events_b


def test_ambiguous_cases_avoid_all_defined_keywords():
    """
    Regression guard: the generated 'insufficient_evidence' cases must
    stay genuinely neutral (no accidental keyword collision), or the
    abstention path they're meant to exercise breaks silently.
    """
    from hypotheses import evaluate_case
    events, cases = generate_dataset(cases_per_type=5, seed=1)
    by_case = {}
    for e in events:
        by_case.setdefault(e[1], []).append(e)
    header = ["event_id", "case_id", "timestamp", "event_type", "user", "device",
              "source_ip", "destination", "process", "severity", "source",
              "label", "description"]
    for case in cases:
        if case[2] != "insufficient_evidence":
            continue
        case_id = case[0]
        events_as_dicts = [dict(zip(header, row)) for row in by_case[case_id]]
        result = evaluate_case(events_as_dicts)
        assert result["abstain"] is True
        assert result["abstain_reason"] == "insufficient_evidence"
