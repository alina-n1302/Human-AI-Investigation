import React from "react";
import { scoreClass } from "../utils.js";

function BaselineRow({ r, maxScore }) {
  return (
    <div className="ev-row">
      <div className="ev-id">{r.event_id}</div>
      <div className="ev-main">
        <div className="ev-type">{r.event_type}</div>
        <div className="ev-desc">{r.description}</div>
        <div className="ev-reasons">
          {(r.baseline_reasons || []).map((x, i) => (
            <span className="reason-chip" key={i}>
              {x}
            </span>
          ))}
        </div>
      </div>
      <div className={`ev-score ${scoreClass(r.baseline_score, maxScore)}`}>
        {r.baseline_score}
      </div>
    </div>
  );
}

function MlRow({ r }) {
  const pct =
    r.ml_score === null || r.ml_score === undefined
      ? null
      : Math.round(r.ml_score * 100);
  return (
    <div className="ev-row">
      <div className="ev-id">{r.event_id}</div>
      <div className="ev-main">
        <div className="ev-type">{r.event_type}</div>
        <div className="ev-desc">{r.description}</div>
        <div className="ev-reasons">
          {(r.ml_reasons || []).map((x, i) => {
            const isPositive = !x.includes("toward benign");
            return (
              <span
                className={`reason-chip ${isPositive ? "reason-chip-ai" : "reason-chip-ai-cool"}`}
                key={i}
              >
                {x}
              </span>
            );
          })}
        </div>
      </div>
      <div
        className={`ev-score ${pct === null ? "score-cool" : scoreClass(pct, 100)}`}
      >
        {pct === null ? "n/a" : `${pct}%`}
      </div>
    </div>
  );
}

export default function EvidencePanel({ baseline, mlRank }) {
  const maxScore = Math.max(...baseline.map((r) => r.baseline_score), 1);

  return (
    <section className="panel active">
      <header className="panel-head">
        <h1>Ranked evidence</h1>
        <p>
          Two independent rankers score every artifact. Compare them &mdash;
          agreement is not proof, and disagreement is a reason to look closer.
          Every score on both sides comes with the specific reasons behind it,
          not just a number to take on faith.
        </p>
      </header>

      <div className="split">
        <div className="split-col">
          <h2 className="split-title">
            Baseline <span className="tag tag-baseline">rule-based</span>
          </h2>
          <div className="table-wrap">
            {baseline.map((r) => (
              <BaselineRow key={r.event_id} r={r} maxScore={maxScore} />
            ))}
          </div>
        </div>
        <div className="split-col">
          <h2 className="split-title">
            AI ranker <span className="tag tag-ai">logistic regression</span>
          </h2>
          <div className="table-wrap">
            {mlRank.map((r) => (
              <MlRow key={r.event_id} r={r} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
