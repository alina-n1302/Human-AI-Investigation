import React from "react";
import { prettyAbstainReason } from "../utils.js";

const META_KEYS = new Set([
  "leading_hypothesis",
  "abstain",
  "abstain_reason",
  "evidence_score_gap",
  "missing_evidence",
]);

function HypCard({ id, data, isLeading }) {
  return (
    <div className={`hyp-card${isLeading ? " leading" : ""}`}>
      <div className="hyp-name">
        {data.label} {isLeading ? "\u2014 leading" : ""}
      </div>
      <div className="hyp-score">evidence-score: {data.score}</div>

      <div className="hyp-section-label">Supporting evidence</div>
      {data.support.length ? (
        data.support.map((s, i) => (
          <div className="hyp-item support" key={i}>
            <b>{s.event_id}</b> &mdash; {s.why.join(", ")}
          </div>
        ))
      ) : (
        <div className="hyp-item">none found</div>
      )}

      <div className="hyp-section-label">Contradicting evidence</div>
      {data.contradict.length ? (
        data.contradict.map((s, i) => (
          <div className="hyp-item contradict" key={i}>
            <b>{s.event_id}</b> &mdash; {s.why.join(", ")}
          </div>
        ))
      ) : (
        <div className="hyp-item">none found</div>
      )}
    </div>
  );
}

export default function HypothesesPanel({ result, hypothesisModel }) {
  const hypothesisIds = Object.keys(result).filter((k) => !META_KEYS.has(k));

  return (
    <section className="panel active">
      <header className="panel-head">
        <h1>Competing hypotheses</h1>
        <p>
          The assistant never renders a verdict. It shows what supports and
          contradicts each explanation, and abstains when the evidence doesn't
          clearly point anywhere.
        </p>
      </header>

      {result.abstain && (
        <div className="abstain-banner">
          The assistant is abstaining &mdash;{" "}
          {prettyAbstainReason(result.abstain_reason)}.
          {result.missing_evidence.length > 0 && (
            <> Missing evidence: {result.missing_evidence.join("; ")}.</>
          )}
        </div>
      )}

      <p
        style={{
          fontSize: ".78rem",
          color: "var(--text-dim)",
          margin: "0 0 1rem",
        }}
      >
        Evidence-score gap between the top two hypotheses:{" "}
        <b>{result.evidence_score_gap}</b> (a count of matched keywords, not a
        probability)
      </p>

      <div className="hyp-grid">
        {hypothesisIds.map((id) => (
          <HypCard
            key={id}
            id={id}
            data={result[id]}
            isLeading={result.leading_hypothesis === id}
          />
        ))}
      </div>

      {hypothesisModel && !hypothesisModel.error && (
        <div className="model-probs-box" style={{ marginTop: "2rem" }}>
          <h2 className="split-title">
            Learned model probabilities{" "}
            <span className="tag tag-ai">experimental</span>
          </h2>
          <p
            style={{
              fontSize: ".76rem",
              color: "var(--text-dim)",
              marginBottom: ".75rem",
            }}
          >
            {hypothesisModel.caveat}
          </p>
          {Object.entries(hypothesisModel.probabilities)
            .sort((a, b) => b[1] - a[1])
            .map(([id, p]) => (
              <div
                key={id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: ".82rem",
                  padding: ".25rem 0",
                }}
              >
                <span>
                  {id
                    .split("_")
                    .map((w) => w[0].toUpperCase() + w.slice(1))
                    .join(" ")}
                </span>
                <b>{(p * 100).toFixed(1)}%</b>
              </div>
            ))}
        </div>
      )}
    </section>
  );
}
