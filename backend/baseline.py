from datetime import datetime

from config import (
    UNUSUAL_HOUR_START,
    UNUSUAL_HOUR_END,
    KNOWN_OFFICE_IPS,
    RISKY_PROCESSES,
)


def _hour_of(timestamp_str):
    return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").hour


def score_event(event):
    score = 0
    reasons = []

    hour = _hour_of(event["timestamp"])
    if UNUSUAL_HOUR_START <= hour <= UNUSUAL_HOUR_END:
        score += 2
        reasons.append("occurred during an unusual hour (midnight-5am)")

    if event["event_type"] == "login_failed":
        score += 2
        reasons.append("failed login attempt")

    if event["source_ip"] not in KNOWN_OFFICE_IPS and event["source_ip"] != "n/a":
        score += 2
        reasons.append("source IP is not on the known office IP list")

    if event["process"] in RISKY_PROCESSES:
        score += 1
        reasons.append("a scripting tool (PowerShell) was launched")

    if event["severity"] == "high":
        score += 2
        reasons.append("source log marked this event as high severity")

    if (
        "malicious" in event["destination"].lower()
        or "c2" in event["destination"].lower()
    ):
        score += 4
        reasons.append("destination matches a known-bad domain pattern")

    return score, reasons


def rank_events(events):
    ranked = []
    for event in events:
        score, reasons = score_event(event)
        ranked.append({**event, "baseline_score": score, "baseline_reasons": reasons})

    ranked.sort(key=lambda e: e["baseline_score"], reverse=True)
    return ranked


if __name__ == "__main__":
    from data_loader import load_events

    for row in rank_events(load_events()):
        print(row["event_id"], row["baseline_score"], row["baseline_reasons"])
