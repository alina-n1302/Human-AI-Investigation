from collections import Counter

from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction import DictVectorizer

from baseline import score_event, _hour_of, KNOWN_OFFICE_IPS, RISKY_PROCESSES


def case_features(events):
    if not events:
        return {"n_events": 0}

    n = len(events)
    severities = Counter(e["severity"] for e in events)
    labels = Counter(e["label"] for e in events)
    hours = [_hour_of(e["timestamp"]) for e in events]
    baseline_scores = [score_event(e)[0] for e in events]
    distinct_ips = {e["source_ip"] for e in events if e["source_ip"] != "n/a"}
    known_ip_events = sum(1 for e in events if e["source_ip"] in KNOWN_OFFICE_IPS)
    risky_process_events = sum(1 for e in events if e["process"] in RISKY_PROCESSES)

    return {
        "n_events": n,
        "frac_high_severity": round(severities.get("high", 0) / n, 3),
        "frac_medium_severity": round(severities.get("medium", 0) / n, 3),
        "frac_low_severity": round(severities.get("low", 0) / n, 3),
        "frac_suspicious_label": round(labels.get("suspicious", 0) / n, 3),
        "frac_context_label": round(labels.get("context", 0) / n, 3),
        "frac_unusual_hour": round(sum(1 for h in hours if h <= 5) / n, 3),
        "frac_known_ip": round(known_ip_events / n, 3),
        "has_risky_process": int(risky_process_events > 0),
        "n_distinct_source_ips": len(distinct_ips),
        "mean_baseline_score": round(sum(baseline_scores) / n, 3),
        "max_baseline_score": max(baseline_scores),
    }


def train_classifier(cases_with_events, labels):
    X_raw = [case_features(events) for events in cases_with_events]
    vectorizer = DictVectorizer(sparse=False)
    X = vectorizer.fit_transform(X_raw)
    model = LogisticRegression(max_iter=2000)
    model.fit(X, labels)
    return model, vectorizer


def predict_case(events, model, vectorizer):
    X = vectorizer.transform([case_features(events)])
    probs = model.predict_proba(X)[0]
    return {str(cls): round(float(p), 3) for cls, p in zip(model.classes_, probs)}


def classify_case_holdout(case_id, events_by_case, labels_by_case):
    train_case_ids = [cid for cid in events_by_case if cid != case_id]
    if not train_case_ids:
        raise ValueError(f"No training data available outside case {case_id!r}.")
    train_events = [events_by_case[cid] for cid in train_case_ids]
    train_labels = [labels_by_case[cid] for cid in train_case_ids]
    model, vectorizer = train_classifier(train_events, train_labels)
    return predict_case(events_by_case[case_id], model, vectorizer)


if __name__ == "__main__":
    from data_loader import load_generated_events, load_generated_cases

    all_events = load_generated_events()
    all_cases = load_generated_cases()

    events_by_case = {}
    for e in all_events:
        events_by_case.setdefault(e["case_id"], []).append(e)
    labels_by_case = {c["case_id"]: c["ground_truth_hypothesis"] for c in all_cases}

    demo_case_id = all_cases[0]["case_id"]
    probs = classify_case_holdout(demo_case_id, events_by_case, labels_by_case)
    print(f"{demo_case_id} (true label: {labels_by_case[demo_case_id]})")
    for hyp, p in sorted(probs.items(), key=lambda x: -x[1]):
        print(f"  {hyp}: {p}")
