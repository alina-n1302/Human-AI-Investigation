import React from "react";
import { prettyHyp } from "../utils.js";

const META_KEYS = new Set([
  "summary",
  "clean_leading_hypothesis",
  "clean_abstain",
]);

export default function RobustnessPanel({ report }) {
  const rows = Object.entries(report).filter(
    ([k]) => !META_KEYS.has(k) && !k.startsWith("clean_"),
  );
  const summary = report.summary || {};

  return (
    <section className="panel active">
      <header className="panel-head">
        <h1>Robustness under evidence corruption</h1>
        <p>
          The same case, replayed at several severity levels of missing, noisy,
          obfuscated, and delayed evidence. A trustworthy assistant degrades
          gracefully, not silently.
        </p>
      </header>

      <div className="robustness-box">
        <p
          style={{
            fontSize: ".78rem",
            color: "var(--text-dim)",
            marginBottom: ".5rem",
          }}
        >
          Clean-data leading hypothesis:{" "}
          <b>
            {report.clean_abstain
              ? "abstains"
              : prettyHyp(report.clean_leading_hypothesis)}
          </b>
        </p>
        <p
          style={{
            fontSize: ".78rem",
            color: "var(--text-dim)",
            marginBottom: "1rem",
          }}
        >
          Across all {rows.length} perturbation levels &mdash; mean top-3
          overlap:{" "}
          <b>
            {summary.mean_top3_overlap !== undefined
              ? `${(summary.mean_top3_overlap * 100).toFixed(0)}%`
              : "n/a"}
          </b>{" "}
          &middot; conclusion flip rate:{" "}
          <b>
            {summary.flip_rate !== undefined
              ? `${(summary.flip_rate * 100).toFixed(0)}%`
              : "n/a"}
          </b>
        </p>

        <table className="rob-table">
          <thead>
            <tr>
              <th>Perturbation</th>
              <th>Top-3 evidence overlap</th>
              <th>Conclusion</th>
              <th>Perturbed result</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([kind, r]) => (
              <tr key={kind}>
                <td>{kind}</td>
                <td>
                  <div className="overlap-bar-wrap">
                    <div
                      className="overlap-bar"
                      style={{ width: `${r.top3_evidence_overlap * 100}%` }}
                    />
                  </div>
                  {(r.top3_evidence_overlap * 100).toFixed(0)}%
                </td>
                <td className={r.conclusion_flipped ? "flip-yes" : "flip-no"}>
                  {r.conclusion_flipped ? "flipped" : "stable"}
                </td>
                <td>
                  {r.perturbed_abstain
                    ? "abstains"
                    : prettyHyp(r.perturbed_leading_hypothesis)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
