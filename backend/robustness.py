import copy
import random

from config import RANDOM_SEED


def perturb_incomplete(events, rng, fraction=0.2):
    events = copy.deepcopy(events)
    if len(events) <= 1:
        return events
    n_remove = max(1, round(len(events) * fraction))
    n_remove = min(n_remove, len(events) - 1)
    for _ in range(n_remove):
        idx = rng.randrange(len(events))
        events.pop(idx)
    return events


def perturb_noisy(events, rng, count=1):
    events = copy.deepcopy(events)
    case_id = events[0]["case_id"] if events else "UNKNOWN"
    for i in range(count):
        events.append(
            {
                "event_id": f"NOISE-{i:03d}",
                "case_id": case_id,
                "timestamp": "2026-01-15 09:00:00",
                "event_type": "file_access",
                "user": "unrelated_user",
                "device": "printer-03",
                "source_ip": "10.0.0.99",
                "destination": "print-queue",
                "process": "spooler.exe",
                "severity": "low",
                "source": "file_audit_log",
                "label": "benign",
                "description": "an unrelated employee printed a document",
            }
        )
    return events


def perturb_obfuscated(events, rng, fraction=0.5):
    events = copy.deepcopy(events)
    distinct_ips = sorted(
        {e["source_ip"] for e in events if e["source_ip"] not in ("n/a",)}
    )
    if not distinct_ips:
        return events
    n_targets = max(1, round(len(distinct_ips) * fraction))
    targets = rng.sample(distinct_ips, min(n_targets, len(distinct_ips)))
    mapping = {ip: f"203.0.113.{70 + i}" for i, ip in enumerate(targets)}
    for e in events:
        if e["source_ip"] in mapping:
            e["source_ip"] = mapping[e["source_ip"]]
    return events


def perturb_delayed(events, rng, minutes=180):
    events = copy.deepcopy(events)
    if not events:
        return events
    target = rng.choice(events)
    date_part, time_part = target["timestamp"].split(" ")
    hour, minute, second = (int(x) for x in time_part.split(":"))
    total_minutes = hour * 60 + minute + minutes
    new_hour = (total_minutes // 60) % 24
    new_minute = total_minutes % 60
    target["timestamp"] = f"{date_part} {new_hour:02d}:{new_minute:02d}:{second:02d}"
    return events


PERTURBATIONS = {
    "incomplete_10pct": (perturb_incomplete, {"fraction": 0.10}),
    "incomplete_25pct": (perturb_incomplete, {"fraction": 0.25}),
    "incomplete_40pct": (perturb_incomplete, {"fraction": 0.40}),
    "noisy_1x": (perturb_noisy, {"count": 1}),
    "noisy_3x": (perturb_noisy, {"count": 3}),
    "obfuscated_25pct": (perturb_obfuscated, {"fraction": 0.25}),
    "obfuscated_50pct": (perturb_obfuscated, {"fraction": 0.50}),
    "delayed_5min": (perturb_delayed, {"minutes": 5}),
    "delayed_3h": (perturb_delayed, {"minutes": 180}),
}


def apply_perturbation(events, kind, seed=RANDOM_SEED):
    if kind not in PERTURBATIONS:
        raise ValueError(
            f"Unknown perturbation '{kind}'. Choose from {list(PERTURBATIONS)}"
        )
    func, kwargs = PERTURBATIONS[kind]
    rng = random.Random(seed)
    return func(events, rng, **kwargs)


def top_k_overlap(ranked_a, ranked_b, k=3):
    ids_a = {e["event_id"] for e in ranked_a[:k]}
    ids_b = {e["event_id"] for e in ranked_b[:k]}
    if not ids_a:
        return 1.0
    return len(ids_a & ids_b) / len(ids_a)


def conclusion_flip(clean_result, perturbed_result):
    return clean_result["leading_hypothesis"] != perturbed_result["leading_hypothesis"]


def summarize(per_perturbation_report):
    overlaps = [v["top3_evidence_overlap"] for v in per_perturbation_report.values()]
    flips = [v["conclusion_flipped"] for v in per_perturbation_report.values()]
    if not overlaps:
        return {"mean_top3_overlap": None, "flip_rate": None}
    return {
        "mean_top3_overlap": round(sum(overlaps) / len(overlaps), 3),
        "flip_rate": round(sum(1 for f in flips if f) / len(flips), 3),
    }


if __name__ == "__main__":
    from data_loader import events_for_case
    import baseline
    import hypotheses

    events = events_for_case("CASE001")
    clean_rank = baseline.rank_events(events)
    clean_hyp = hypotheses.evaluate_case(events)

    per_perturbation = {}
    for kind in PERTURBATIONS:
        damaged = apply_perturbation(events, kind)
        damaged_rank = baseline.rank_events(damaged)
        damaged_hyp = hypotheses.evaluate_case(damaged)
        per_perturbation[kind] = {
            "top3_evidence_overlap": top_k_overlap(clean_rank, damaged_rank),
            "conclusion_flipped": conclusion_flip(clean_hyp, damaged_hyp),
        }
        print(
            kind,
            "top3_overlap=",
            per_perturbation[kind]["top3_evidence_overlap"],
            "conclusion_flip=",
            per_perturbation[kind]["conclusion_flipped"],
        )

    print("\nSummary:", summarize(per_perturbation))
