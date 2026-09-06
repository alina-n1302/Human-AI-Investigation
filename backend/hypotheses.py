import re

from config import MIN_SUPPORT_THRESHOLD, DECISION_MARGIN

HYPOTHESES = [
    {
        "id": "credential_compromise",
        "label": "Credential compromise",
        "keywords": [
            "foreign ip",
            "malware",
            "malicious",
            "known to be associated with malware",
            "no maintenance window",
            "unusual",
            "c2",
        ],
    },
    {
        "id": "legitimate_admin_activity",
        "label": "Legitimate administrator activity",
        "keywords": [
            "maintenance ticket",
            "scheduled patch",
            "internal update server",
            "authorizes this exact time window",
            "patch process",
        ],
    },
    {
        "id": "insider_data_exfiltration",
        "label": "Insider data exfiltration",
        "keywords": [
            "unusually large download",
            "personal cloud storage",
            "after resignation",
            "outside normal job duties",
            "bulk transfer",
            "large volume of files",
        ],
    },
]
HYPOTHESIS_IDS = [h["id"] for h in HYPOTHESES]
HYPOTHESIS_BY_ID = {h["id"]: h for h in HYPOTHESES}


NEGATION_CUES = [
    "not ",
    "no longer",
    "ruled out",
    "isn't",
    "wasn't",
    "is not",
    "was not",
    "false positive",
    "cleared of",
    "unrelated to",
    "does not indicate",
    "no evidence of",
]
NEGATION_WINDOW_CHARS = 30


def _matches_any(text, keywords):
    text = text.lower()
    hits = []
    for keyword in keywords:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        match = re.search(pattern, text)
        if not match:
            continue
        idx = match.start()
        window = text[max(0, idx - NEGATION_WINDOW_CHARS) : idx]
        if any(cue in window for cue in NEGATION_CUES):
            continue
        hits.append(keyword)
    return hits


def evaluate_case(events, min_support=None, decision_margin=None):
    min_support = MIN_SUPPORT_THRESHOLD if min_support is None else min_support
    decision_margin = DECISION_MARGIN if decision_margin is None else decision_margin

    result = {
        h["id"]: {"label": h["label"], "support": [], "contradict": [], "score": 0}
        for h in HYPOTHESES
    }

    for event in events:
        text = event["description"]
        hits_by_hyp = {h["id"]: _matches_any(text, h["keywords"]) for h in HYPOTHESES}
        matched_ids = [hid for hid, hits in hits_by_hyp.items() if hits]

        for hid in matched_ids:
            result[hid]["support"].append(
                {"event_id": event["event_id"], "why": hits_by_hyp[hid]}
            )
            result[hid]["score"] += len(hits_by_hyp[hid])

        for hid in matched_ids:
            for other in HYPOTHESIS_IDS:
                if other != hid and other not in matched_ids:
                    result[other]["contradict"].append(
                        {"event_id": event["event_id"], "why": hits_by_hyp[hid]}
                    )

    scores = {hid: result[hid]["score"] for hid in HYPOTHESIS_IDS}
    ranked_ids = sorted(HYPOTHESIS_IDS, key=lambda hid: scores[hid], reverse=True)
    top_id = ranked_ids[0]
    top_score = scores[top_id]
    second_score = scores[ranked_ids[1]] if len(ranked_ids) > 1 else 0
    gap = top_score - second_score

    if top_score < min_support:
        result["leading_hypothesis"] = None
        result["abstain"] = True
        result["abstain_reason"] = "insufficient_evidence"
        result["missing_evidence"] = [
            "no hypothesis reached even minimal keyword support",
            "this may be genuinely ambiguous, or the description language "
            "doesn't match any of the known evidence patterns",
        ]
    elif gap < decision_margin:
        result["leading_hypothesis"] = None
        result["abstain"] = True
        result["abstain_reason"] = "too_close_to_call"
        result["missing_evidence"] = [
            "no change-management ticket found either way",
            "no confirmation from the account owner about the activity",
        ]
    else:
        result["leading_hypothesis"] = top_id
        result["abstain"] = False
        result["abstain_reason"] = None
        result["missing_evidence"] = []

    result["evidence_score_gap"] = gap
    return result


if __name__ == "__main__":
    from data_loader import events_for_case, case_ids
    import json

    for case_id in case_ids():
        print(f"\n--- {case_id} ---")
        print(json.dumps(evaluate_case(events_for_case(case_id)), indent=2))
