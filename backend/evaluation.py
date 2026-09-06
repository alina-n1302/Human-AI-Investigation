import random
from collections import defaultdict

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    brier_score_loss,
)
from sklearn.calibration import calibration_curve

from config import RANDOM_SEED
import baseline
import hypotheses
import robustness
import ml_ranker
from ml_ranker import train_ranker, _score_events, _features_for


def case_level_train_test_split(
    all_events, all_cases, test_fraction=0.25, seed=RANDOM_SEED
):
    rng = random.Random(seed)
    cases_by_type = defaultdict(list)
    for c in all_cases:
        cases_by_type[c["ground_truth_hypothesis"]].append(c["case_id"])

    test_case_ids = set()
    for hyp_type, cids in cases_by_type.items():
        cids = sorted(cids)
        rng.shuffle(cids)
        n_test = max(1, round(len(cids) * test_fraction))
        test_case_ids.update(cids[:n_test])

    all_case_ids = {c["case_id"] for c in all_cases}
    train_case_ids = all_case_ids - test_case_ids

    train_events = [e for e in all_events if e["case_id"] in train_case_ids]
    test_events = [e for e in all_events if e["case_id"] in test_case_ids]
    return train_events, test_events, sorted(train_case_ids), sorted(test_case_ids)


def bootstrap_ci(y_true, y_pred, metric_fn, n_boot=1000, seed=RANDOM_SEED, alpha=0.05):
    rng = random.Random(seed)
    n = len(y_true)
    if n == 0:
        return None, None, None
    stats = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        yt = [y_true[i] for i in idx]
        yp = [y_pred[i] for i in idx]
        try:
            stats.append(metric_fn(yt, yp))
        except Exception:
            continue
    if not stats:
        return metric_fn(y_true, y_pred), None, None
    stats.sort()
    lo_idx = max(0, int((alpha / 2) * len(stats)))
    hi_idx = min(len(stats) - 1, int((1 - alpha / 2) * len(stats)))
    point = metric_fn(y_true, y_pred)
    return round(point, 3), round(stats[lo_idx], 3), round(stats[hi_idx], 3)


def evaluate_ml_ranker_on_split(train_events, test_events, exclude_features=None):
    model, vectorizer = train_ranker(train_events, exclude=exclude_features)
    ranked = _score_events(test_events, model, vectorizer, exclude=exclude_features)
    scored = [e for e in ranked if e["ml_score"] is not None]

    y_true = [1 if e["label"] == "suspicious" else 0 for e in scored]
    y_pred = [1 if e["ml_score"] >= 0.5 else 0 for e in scored]
    y_prob = [e["ml_score"] for e in scored]

    acc, acc_lo, acc_hi = bootstrap_ci(y_true, y_pred, accuracy_score)
    f1, f1_lo, f1_hi = bootstrap_ci(
        y_true, y_pred, lambda a, b: f1_score(a, b, zero_division=0)
    )

    false_positives = [
        e["event_id"] for e, t, p in zip(scored, y_true, y_pred) if t == 0 and p == 1
    ]
    false_negatives = [
        e["event_id"] for e, t, p in zip(scored, y_true, y_pred) if t == 1 and p == 0
    ]

    try:
        brier = round(brier_score_loss(y_true, y_prob), 3)
    except ValueError:
        brier = None

    try:
        frac_pos, mean_pred = calibration_curve(
            y_true, y_prob, n_bins=5, strategy="quantile"
        )
        calibration_bins = [
            {
                "mean_predicted": round(float(p), 3),
                "observed_fraction_positive": round(float(f), 3),
            }
            for p, f in zip(mean_pred, frac_pos)
        ]
    except (ValueError, IndexError):
        calibration_bins = []

    return {
        "n_test_events": len(scored),
        "accuracy": acc,
        "accuracy_ci95": [acc_lo, acc_hi],
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 3),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 3),
        "f1": f1,
        "f1_ci95": [f1_lo, f1_hi],
        "brier_score": brier,
        "calibration_bins": calibration_bins,
        "false_positive_event_ids": false_positives,
        "false_negative_event_ids": false_negatives,
    }


ALL_FEATURES = [
    "hour",
    "is_unusual_hour",
    "event_type",
    "is_known_ip",
    "is_risky_process",
    "severity",
    "source",
]


def ablation_study(train_events, test_events):
    baseline_result = evaluate_ml_ranker_on_split(train_events, test_events)
    rows = [
        {
            "removed_feature": None,
            "accuracy": baseline_result["accuracy"],
            "accuracy_delta": 0.0,
        }
    ]
    for feat in ALL_FEATURES:
        result = evaluate_ml_ranker_on_split(
            train_events, test_events, exclude_features={feat}
        )
        delta = (
            round(result["accuracy"] - baseline_result["accuracy"], 3)
            if result["accuracy"] is not None
            else None
        )
        rows.append(
            {
                "removed_feature": feat,
                "accuracy": result["accuracy"],
                "accuracy_delta": delta,
            }
        )
    return rows


def explain_model(train_events):
    model, vectorizer = train_ranker(train_events)
    names = vectorizer.get_feature_names_out()
    coefs = model.coef_[0]
    ranked = sorted(zip(names, coefs), key=lambda x: abs(x[1]), reverse=True)
    return [{"feature": n, "coefficient": round(float(c), 3)} for n, c in ranked]


def sensitivity_analysis(
    events_by_case,
    ground_truth_by_case,
    min_support_values=(1, 2, 3),
    decision_margin_values=(1, 2, 3),
):
    rows = []
    for min_support in min_support_values:
        for margin in decision_margin_values:
            n_cases = 0
            n_abstain = 0
            n_correct = 0
            for case_id, events in events_by_case.items():
                truth = ground_truth_by_case.get(case_id)
                if truth is None:
                    continue
                n_cases += 1
                result = hypotheses.evaluate_case(
                    events, min_support=min_support, decision_margin=margin
                )
                if result["abstain"]:
                    n_abstain += 1
                    if truth == "insufficient_evidence":
                        n_correct += 1
                else:
                    if result["leading_hypothesis"] == truth:
                        n_correct += 1
            rows.append(
                {
                    "min_support_threshold": min_support,
                    "decision_margin": margin,
                    "abstain_rate": round(n_abstain / n_cases, 3) if n_cases else None,
                    "accuracy": round(n_correct / n_cases, 3) if n_cases else None,
                    "n_cases": n_cases,
                }
            )
    return rows


def robustness_across_dataset(events_by_case, seed=RANDOM_SEED):
    per_perturbation = defaultdict(lambda: {"overlaps": [], "flips": []})

    for case_id, events in events_by_case.items():
        clean_rank = baseline.rank_events(events)
        clean_hyp = hypotheses.evaluate_case(events)
        for kind in robustness.PERTURBATIONS:
            damaged = robustness.apply_perturbation(events, kind, seed=seed)
            damaged_rank = baseline.rank_events(damaged)
            damaged_hyp = hypotheses.evaluate_case(damaged)
            per_perturbation[kind]["overlaps"].append(
                robustness.top_k_overlap(clean_rank, damaged_rank)
            )
            per_perturbation[kind]["flips"].append(
                robustness.conclusion_flip(clean_hyp, damaged_hyp)
            )

    rows = []
    for kind, data in per_perturbation.items():
        overlaps = data["overlaps"]
        flips = [1 if f else 0 for f in data["flips"]]
        _, flip_lo, flip_hi = (
            bootstrap_ci(flips, flips, lambda a, b: sum(a) / len(a))
            if flips
            else (None, None, None)
        )
        rows.append(
            {
                "perturbation": kind,
                "n_cases": len(overlaps),
                "mean_top3_overlap": (
                    round(sum(overlaps) / len(overlaps), 3) if overlaps else None
                ),
                "flip_rate": round(sum(flips) / len(flips), 3) if flips else None,
                "flip_rate_ci95": [flip_lo, flip_hi],
            }
        )
    return sorted(rows, key=lambda r: r["perturbation"])
