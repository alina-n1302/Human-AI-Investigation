import json
import os
import time
from collections import defaultdict

import data_loader
import evaluation
from config import RANDOM_SEED, CASES_PER_HYPOTHESIS_TYPE

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def main():
    t_start = time.time()
    lines = []

    def log(msg=""):
        print(msg)
        lines.append(msg)

    log(f"# Experiment report (seed={RANDOM_SEED})\n")

    try:
        all_events = data_loader.load_generated_events()
        all_cases = data_loader.load_generated_cases()
    except FileNotFoundError:
        log(
            "Generated dataset not found. Run `python backend/case_generator.py` first."
        )
        return
    log(
        f"Loaded {len(all_events)} events across {len(all_cases)} generated cases "
        f"({CASES_PER_HYPOTHESIS_TYPE} per hypothesis type).\n"
    )

    events_by_case = defaultdict(list)
    for e in all_events:
        events_by_case[e["case_id"]].append(e)
    labels_by_case = {c["case_id"]: c["ground_truth_hypothesis"] for c in all_cases}

    train_ev, test_ev, train_ids, test_ids = evaluation.case_level_train_test_split(
        all_events, all_cases
    )
    log("## Case-level train/test split")
    log(
        f"- {len(train_ids)} training cases, {len(test_ids)} test cases "
        f"(grouped by case, stratified by hypothesis - never split within a case)\n"
    )

    log("## ML ranker (logistic regression) - held-out evaluation")
    ml_result = evaluation.evaluate_ml_ranker_on_split(train_ev, test_ev)
    log(f"- accuracy: {ml_result['accuracy']} (95% CI {ml_result['accuracy_ci95']})")
    log(f"- precision: {ml_result['precision']}, recall: {ml_result['recall']}")
    log(f"- F1: {ml_result['f1']} (95% CI {ml_result['f1_ci95']})")
    log(f"- Brier score (calibration, lower=better): {ml_result['brier_score']}")
    log(
        f"- false positives: {len(ml_result['false_positive_event_ids'])}, "
        f"false negatives: {len(ml_result['false_negative_event_ids'])}"
    )
    log(f"- calibration bins: {ml_result['calibration_bins']}\n")

    log("## Ablation study (which features matter)")
    ablation = evaluation.ablation_study(train_ev, test_ev)
    for row in ablation:
        removed = row["removed_feature"] or "(none - full model)"
        log(
            f"- removed {removed}: accuracy={row['accuracy']} (delta {row['accuracy_delta']})"
        )
    log("")

    log("## Explainability - top model coefficients")
    for row in evaluation.explain_model(train_ev)[:8]:
        log(f"- {row['feature']}: {row['coefficient']}")
    log("")

    log("## Sensitivity analysis - hypothesis engine thresholds")
    sens = evaluation.sensitivity_analysis(events_by_case, labels_by_case)
    for row in sens:
        log(
            f"- min_support={row['min_support_threshold']}, margin={row['decision_margin']}: "
            f"abstain_rate={row['abstain_rate']}, accuracy={row['accuracy']}"
        )
    log("")

    log("## Robustness - aggregated across all 160 cases")
    rob = evaluation.robustness_across_dataset(events_by_case)
    for row in rob:
        log(
            f"- {row['perturbation']}: mean_top3_overlap={row['mean_top3_overlap']}, "
            f"flip_rate={row['flip_rate']} (95% CI {row['flip_rate_ci95']}), n={row['n_cases']}"
        )
    log("")

    elapsed = round(time.time() - t_start, 1)
    log(f"---\nTotal runtime: {elapsed}s")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    report_path = os.path.join(RESULTS_DIR, "experiment_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nWrote {report_path}")


if __name__ == "__main__":
    main()
