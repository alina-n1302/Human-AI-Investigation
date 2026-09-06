from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from baseline import KNOWN_OFFICE_IPS, RISKY_PROCESSES, _hour_of


def _features_for(event, exclude=None):
    hour = _hour_of(event["timestamp"])
    features = {
        "hour": hour,
        "is_unusual_hour": int(hour <= 5),
        "event_type": event["event_type"],
        "is_known_ip": int(event["source_ip"] in KNOWN_OFFICE_IPS),
        "is_risky_process": int(event["process"] in RISKY_PROCESSES),
        "severity": event["severity"],
        "source": event["source"],
    }
    if exclude:
        for key in exclude:
            features.pop(key, None)
    return features


def train_ranker(training_events, exclude=None):
    usable = [e for e in training_events if e["label"] in ("benign", "suspicious")]
    X_raw = [_features_for(e, exclude=exclude) for e in usable]
    y = [1 if e["label"] == "suspicious" else 0 for e in usable]

    vectorizer = DictVectorizer(sparse=False)
    X = vectorizer.fit_transform(X_raw)

    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    return model, vectorizer


def explain_event(event, model, vectorizer, exclude=None, top_n=4):
    features = _features_for(event, exclude=exclude)
    X = vectorizer.transform([features])
    names = vectorizer.get_feature_names_out()
    coefficients = model.coef_[0]

    contributions = [
        {"feature": name, "contribution": round(float(coef * value), 3)}
        for name, coef, value in zip(names, coefficients, X[0])
        if value != 0
    ]
    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)
    return contributions[:top_n]


def _explanation_to_reasons(contributions):
    reasons = []
    for c in contributions:
        direction = "toward suspicious" if c["contribution"] > 0 else "toward benign"
        reasons.append(f"{c['feature']} ({c['contribution']:+.2f} {direction})")
    return reasons


NON_EVIDENCE_EVENT_TYPES = {"analyst_note"}


def _score_events(events, model, vectorizer, exclude=None):
    ranked = []
    for event in events:
        if event.get("event_type") in NON_EVIDENCE_EVENT_TYPES:
            ranked.append(
                {**event, "ml_score": None, "ml_explanation": [], "ml_reasons": []}
            )
            continue
        X = vectorizer.transform([_features_for(event, exclude=exclude)])
        probability_suspicious = float(model.predict_proba(X)[0][1])
        contributions = explain_event(event, model, vectorizer, exclude=exclude)
        ranked.append(
            {
                **event,
                "ml_score": round(probability_suspicious, 3),
                "ml_explanation": contributions,
                "ml_reasons": _explanation_to_reasons(contributions),
            }
        )

    scored = [r for r in ranked if r["ml_score"] is not None]
    unscored = [r for r in ranked if r["ml_score"] is None]
    scored.sort(key=lambda e: e["ml_score"], reverse=True)
    return scored + unscored


def rank_events(events, model=None, vectorizer=None):
    if model is None or vectorizer is None:
        model, vectorizer = train_ranker(events)
    return _score_events(events, model, vectorizer)


def rank_events_holdout(case_id, all_events):
    training = [e for e in all_events if e["case_id"] != case_id]
    target = [e for e in all_events if e["case_id"] == case_id]
    if not training:
        raise ValueError(
            f"No training data available outside case {case_id!r} - "
            "need at least one other case in the dataset."
        )
    model, vectorizer = train_ranker(training)
    return _score_events(target, model, vectorizer)


def evaluate_holdout(all_events, case_ids):
    results = []
    for case_id in case_ids:
        ranked = rank_events_holdout(case_id, all_events)
        scored = [e for e in ranked if e["ml_score"] is not None]
        if not scored:
            continue
        y_true = [1 if e["label"] == "suspicious" else 0 for e in scored]
        y_pred = [1 if e["ml_score"] >= 0.5 else 0 for e in scored]
        results.append(
            {
                "case_id": case_id,
                "n_events": len(scored),
                "accuracy": round(accuracy_score(y_true, y_pred), 3),
                "precision": round(precision_score(y_true, y_pred, zero_division=0), 3),
                "recall": round(recall_score(y_true, y_pred, zero_division=0), 3),
                "f1": round(f1_score(y_true, y_pred, zero_division=0), 3),
            }
        )
    return results


if __name__ == "__main__":
    from data_loader import load_events, case_ids

    all_events = load_events()
    ids = case_ids()

    print("Leave-one-case-out evaluation (each case scored by a model that")
    print("never saw that case during training):\n")
    for row in evaluate_holdout(all_events, ids):
        print(
            f"  {row['case_id']}: acc={row['accuracy']} "
            f"precision={row['precision']} recall={row['recall']} f1={row['f1']} "
            f"(n={row['n_events']})"
        )

    print("\nPer-event holdout scores for CASE001, with explanations:")
    for row in rank_events_holdout("CASE001", all_events):
        print(" ", row["event_id"], row["ml_score"])
        for reason in row["ml_reasons"]:
            print("     -", reason)
