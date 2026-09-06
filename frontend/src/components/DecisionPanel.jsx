import React, { useState } from "react";
import { recordDecision } from "../api.js";

export default function DecisionPanel({
  caseId,
  investigatorName,
  hypothesisTypes,
  caseLoadedAt,
  onDecisionRecorded,
}) {
  const firstHypId = hypothesisTypes[0]?.id || "credential_compromise";
  const [hypothesis, setHypothesis] = useState(firstHypId);
  const [agreement, setAgreement] = useState("true");
  const [studyGroup, setStudyGroup] = useState("B");
  const [rationale, setRationale] = useState("");
  const [status, setStatus] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus("Recording...");

    const timeToDecisionSeconds = caseLoadedAt
      ? Math.round((Date.now() - caseLoadedAt) / 1000)
      : null;

    const payload = {
      case_id: caseId,
      investigator_name: investigatorName || "anonymous",
      chosen_hypothesis: hypothesis,
      agreed_with_ai: agreement === "true",
      rationale,
      study_group: studyGroup,
      time_to_decision_seconds: timeToDecisionSeconds,
    };

    await recordDecision(payload);

    setStatus("Decision recorded to the audit log.");
    await onDecisionRecorded();
  }

  return (
    <section className="panel active">
      <header className="panel-head">
        <h1>Record the investigator's decision</h1>
        <p>
          This is the only write action in the system. The AI cannot take it
          &mdash; only you can.
        </p>
      </header>

      <form className="decision-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Final hypothesis</span>
          <select
            value={hypothesis}
            onChange={(e) => setHypothesis(e.target.value)}
          >
            {hypothesisTypes.map((h) => (
              <option key={h.id} value={h.id}>
                {h.label}
              </option>
            ))}
            <option value="inconclusive">
              Inconclusive &mdash; more evidence needed
            </option>
          </select>
        </label>

        <label className="field">
          <span>Did this match the AI's leading hypothesis?</span>
          <select
            value={agreement}
            onChange={(e) => setAgreement(e.target.value)}
          >
            <option value="true">Yes, agreed</option>
            <option value="false">No, overrode the AI</option>
          </select>
        </label>

        <label className="field">
          <span>
            Study group{" "}
            <span
              style={{
                fontWeight: 400,
                color: "var(--text-dim)",
                fontSize: ".75rem",
              }}
            >
              (infrastructure for a future controlled study &mdash; see README)
            </span>
          </span>
          <select
            value={studyGroup}
            onChange={(e) => setStudyGroup(e.target.value)}
          >
            <option value="B">B &mdash; full AI assistance</option>
            <option value="A">A &mdash; no AI assistance</option>
          </select>
        </label>

        <label className="field field-wide">
          <span>Rationale</span>
          <textarea
            rows={4}
            placeholder="Cite the specific evidence that drove this conclusion..."
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
          />
        </label>

        <button type="submit" className="btn-record">
          Record decision
        </button>
        <p className="decision-status">{status}</p>
      </form>
    </section>
  );
}
