import os
from flask import Flask, jsonify, request, send_from_directory

from flask_cors import CORS

import data_loader
import baseline
import ml_ranker
import timeline
import event_graph
import hypotheses
import hypothesis_classifier
import robustness
import audit_log
import uploads
from config import FLASK_PORT, CORS_ORIGINS

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path="")


CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})


@app.route("/")
def serve_index():
    if os.path.exists(os.path.join(FRONTEND_DIST, "index.html")):
        return send_from_directory(FRONTEND_DIST, "index.html")
    return (
        "Frontend build not found. Run 'npm install && npm run build' "
        "inside the frontend/ folder, or run the Vite dev server with "
        "'npm run dev' and open http://127.0.0.1:5173 instead.",
        200,
    )


@app.route("/<path:path>")
def serve_static_assets(path):
    full_path = os.path.join(FRONTEND_DIST, path)
    if os.path.exists(full_path):
        return send_from_directory(FRONTEND_DIST, path)
    return serve_index()


def get_events_for_case(case_id):
    if uploads.is_uploaded_case(case_id):
        return uploads.events_for_uploaded_case(case_id)
    return data_loader.events_for_case(case_id)


def get_training_pool(case_id):
    pool = data_loader.load_events()
    if uploads.is_uploaded_case(case_id):
        pool = pool + uploads.events_for_uploaded_case(case_id)
    return pool


@app.route("/api/cases")
def api_cases():
    return jsonify(data_loader.load_cases() + uploads.list_uploaded_cases())


@app.route("/api/cases/upload", methods=["POST"])
def api_upload_case():
    if "file" not in request.files:
        return jsonify({"error": "no file was attached to the request"}), 400
    uploaded_file = request.files["file"]
    if not uploaded_file.filename:
        return jsonify({"error": "no file was selected"}), 400

    try:
        case_id = uploads.parse_upload(uploaded_file.stream, uploaded_file.filename)
    except uploads.UploadError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"case_id": case_id, "filename": uploaded_file.filename}), 201


@app.route("/api/cases/<case_id>/events")
def api_events(case_id):
    return jsonify(get_events_for_case(case_id))


@app.route("/api/cases/<case_id>/baseline")
def api_baseline(case_id):
    events = get_events_for_case(case_id)
    return jsonify(baseline.rank_events(events))


@app.route("/api/cases/<case_id>/ml-rank")
def api_ml_rank(case_id):
    all_events = get_training_pool(case_id)
    return jsonify(ml_ranker.rank_events_holdout(case_id, all_events))


@app.route("/api/hypotheses")
def api_hypothesis_types():
    return jsonify(
        [{"id": h["id"], "label": h["label"]} for h in hypotheses.HYPOTHESES]
    )


@app.route("/api/cases/<case_id>/hypothesis-model")
def api_hypothesis_model(case_id):
    all_cases = data_loader.load_cases()
    all_events = get_training_pool(case_id)
    events_by_case = {}
    for e in all_events:
        events_by_case.setdefault(e["case_id"], []).append(e)
    labels_by_case = {c["case_id"]: c["ground_truth_hypothesis"] for c in all_cases}

    try:
        probabilities = hypothesis_classifier.classify_case_holdout(
            case_id, events_by_case, labels_by_case
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(
        {
            "probabilities": probabilities,
            "caveat": "trained on only 3 other demo cases - illustrative, not "
            "statistically meaningful. See run_experiments.py for the "
            "real evaluation on 160 generated cases.",
        }
    )


@app.route("/api/cases/<case_id>/timeline")
def api_timeline(case_id):
    events = get_events_for_case(case_id)
    return jsonify(
        {
            "timeline": timeline.build_timeline(events),
            "conflicts": timeline.find_conflicts(events),
            "entity_links": timeline.build_entity_links(events),
        }
    )


@app.route("/api/cases/<case_id>/event-graph")
def api_event_graph(case_id):
    events = get_events_for_case(case_id)
    return jsonify(event_graph.build_graph(events))


@app.route("/api/cases/<case_id>/hypotheses")
def api_hypotheses(case_id):
    events = get_events_for_case(case_id)
    result = hypotheses.evaluate_case(events)

    if request.args.get("inject_error", "").lower() in ("1", "true", "yes"):
        real_leader = result["leading_hypothesis"]
        other_ids = [h for h in hypotheses.HYPOTHESIS_IDS if h != real_leader]
        if other_ids:
            result = dict(result)
            result["leading_hypothesis"] = other_ids[0]
            result["abstain"] = False
            result["abstain_reason"] = None
            result["_error_injected"] = True

    return jsonify(result)


@app.route("/api/cases/<case_id>/robustness")
def api_robustness(case_id):
    events = get_events_for_case(case_id)
    clean_rank = baseline.rank_events(events)
    clean_hyp = hypotheses.evaluate_case(events)

    report = {}
    for kind in robustness.PERTURBATIONS:
        damaged_events = robustness.apply_perturbation(events, kind)
        damaged_rank = baseline.rank_events(damaged_events)
        damaged_hyp = hypotheses.evaluate_case(damaged_events)

        report[kind] = {
            "top3_evidence_overlap": round(
                robustness.top_k_overlap(clean_rank, damaged_rank), 2
            ),
            "conclusion_flipped": robustness.conclusion_flip(clean_hyp, damaged_hyp),
            "perturbed_leading_hypothesis": damaged_hyp["leading_hypothesis"],
            "perturbed_abstain": damaged_hyp["abstain"],
        }

    report["summary"] = robustness.summarize(report)
    report["clean_leading_hypothesis"] = clean_hyp["leading_hypothesis"]
    report["clean_abstain"] = clean_hyp["abstain"]
    return jsonify(report)


@app.route("/api/decisions", methods=["POST"])
def api_record_decision():
    body = request.get_json(force=True)
    entry = audit_log.record_decision(
        case_id=body.get("case_id", ""),
        investigator_name=body.get("investigator_name", "anonymous"),
        chosen_hypothesis=body.get("chosen_hypothesis", ""),
        rationale=body.get("rationale", ""),
        agreed_with_ai=body.get("agreed_with_ai"),
        study_group=body.get("study_group"),
        time_to_decision_seconds=body.get("time_to_decision_seconds"),
    )
    return jsonify(entry), 201


@app.route("/api/decisions")
def api_list_decisions():
    return jsonify(audit_log.read_all_decisions())


@app.route("/api/decisions/verify")
def api_verify_decisions():
    return jsonify(audit_log.verify_chain())


if __name__ == "__main__":
    app.run(debug=True, port=FLASK_PORT)
