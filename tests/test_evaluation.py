from evaluation import case_level_train_test_split, bootstrap_ci


def _fake_cases_and_events():
    cases = [
        {"case_id": f"C{i}", "ground_truth_hypothesis": "type_a" if i % 2 == 0 else "type_b"}
        for i in range(20)
    ]
    events = []
    for c in cases:
        for j in range(3):
            events.append({"case_id": c["case_id"], "event_id": f"{c['case_id']}-E{j}",
                            "label": "benign"})
    return cases, events


def test_split_is_case_level_not_event_level():
    """
    The core regression test for the review's explicit ask: no case's
    events should appear in both train and test.
    """
    cases, events = _fake_cases_and_events()
    train_ev, test_ev, train_ids, test_ids = case_level_train_test_split(events, cases)
    assert set(train_ids).isdisjoint(set(test_ids))

    train_case_ids_in_events = {e["case_id"] for e in train_ev}
    test_case_ids_in_events = {e["case_id"] for e in test_ev}
    assert train_case_ids_in_events.isdisjoint(test_case_ids_in_events)


def test_split_is_stratified_by_hypothesis():
    cases, events = _fake_cases_and_events()
    _, _, train_ids, test_ids = case_level_train_test_split(events, cases)
    train_types = {c["ground_truth_hypothesis"] for c in cases if c["case_id"] in train_ids}
    test_types = {c["ground_truth_hypothesis"] for c in cases if c["case_id"] in test_ids}
    assert "type_a" in train_types and "type_b" in train_types
    assert "type_a" in test_types and "type_b" in test_types


def test_split_is_reproducible_with_same_seed():
    cases, events = _fake_cases_and_events()
    _, _, ids_a, _ = case_level_train_test_split(events, cases, seed=5)
    _, _, ids_b, _ = case_level_train_test_split(events, cases, seed=5)
    assert ids_a == ids_b


def test_bootstrap_ci_bounds_contain_point_estimate():
    y_true = [1, 1, 1, 0, 0, 1, 0, 1, 1, 0]
    y_pred = [1, 1, 0, 0, 0, 1, 0, 1, 1, 0]
    from sklearn.metrics import accuracy_score
    point, lo, hi = bootstrap_ci(y_true, y_pred, accuracy_score, n_boot=200, seed=1)
    assert lo <= point <= hi
    assert 0.0 <= lo and hi <= 1.0
