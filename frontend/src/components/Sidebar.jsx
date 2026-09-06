import React, { useRef, useState } from "react";
import { prettyHyp, shortHash } from "../utils.js";

export default function Sidebar({
  cases,
  currentCaseId,
  onCaseChange,
  scenario,
  investigatorName,
  onInvestigatorNameChange,
  decisions,
  integrity,
  onUploadCase,
}) {
  const fileInputRef = useRef(null);
  const [uploadState, setUploadState] = useState({
    status: "idle",
    message: "",
  });

  const handleFileChosen = async (e) => {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    setUploadState({ status: "uploading", message: "" });
    try {
      await onUploadCase(file);
      setUploadState({ status: "idle", message: "" });
    } catch (err) {
      setUploadState({ status: "error", message: err.message });
    }
  };

  return (
    <aside className="rail">
      <div className="rail-brand">
        <span className="rail-mark">§</span>
        <div>
          <div className="rail-title">Case File</div>
          <div className="rail-sub">Human&ndash;AI Investigation Lab</div>
        </div>
      </div>

      <div className="rail-block">
        <div className="rail-label">Open case</div>
        <select
          className="case-select"
          value={currentCaseId || ""}
          onChange={(e) => onCaseChange(e.target.value)}
        >
          {cases.map((c) => (
            <option key={c.case_id} value={c.case_id}>
              {c.case_id}
            </option>
          ))}
        </select>
        <p className="rail-note">{scenario}</p>
      </div>

      <div className="rail-block">
        <div className="rail-label">Bring your own data</div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileChosen}
          style={{ display: "none" }}
        />
        <button
          type="button"
          className="btn-upload"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadState.status === "uploading"}
        >
          {uploadState.status === "uploading" ? "Uploading…" : "Upload a CSV"}
        </button>
        <p className="rail-note">
          A CSV with columns like timestamp, event_type, user, device,
          source_ip, destination, process, severity, source, description. It
          runs through the same ranking, timeline, hypotheses, and graph as
          every other case. Nothing is saved to disk &mdash; it only lives as
          long as the server keeps running.
        </p>
        {uploadState.status === "error" && (
          <p className="rail-note upload-error">{uploadState.message}</p>
        )}
      </div>

      <div className="rail-block">
        <div className="rail-label">Investigator</div>
        <input
          className="rail-input"
          type="text"
          placeholder="your name"
          value={investigatorName}
          onChange={(e) => onInvestigatorNameChange(e.target.value)}
        />
      </div>

      <div className="rail-block rail-role">
        <div className="rail-label">System role</div>
        <p className="rail-note">
          The assistant ranks evidence, drafts a timeline, and compares
          hypotheses. It cannot close a case. Only the investigator, below,
          records a final decision.
        </p>
      </div>

      <div className="rail-block rail-audit">
        <div className="rail-label">Audit trail</div>

        {integrity && (
          <div
            className={`integrity-badge ${integrity.valid ? "integrity-ok" : "integrity-bad"}`}
          >
            {integrity.valid
              ? `✓ hash chain intact (${integrity.checked} entries)`
              : `✗ tampering detected at entry ${integrity.broken_at_line}`}
            {integrity.legacy_entries > 0 && (
              <span className="integrity-legacy">
                {" "}
                &middot; {integrity.legacy_entries} legacy (pre-hash)
              </span>
            )}
          </div>
        )}

        <div className="audit-list">
          {decisions.length === 0 ? (
            <p className="rail-note">No decisions recorded yet.</p>
          ) : (
            decisions
              .slice(-6)
              .reverse()
              .map((d, i) => (
                <div className="audit-entry" key={i}>
                  <div className="what">{prettyHyp(d.chosen_hypothesis)}</div>
                  <div className="who">
                    {d.case_id} &middot; {d.investigator_name}
                  </div>
                  {d.entry_hash && (
                    <div className="hash">sha256 {shortHash(d.entry_hash)}</div>
                  )}
                </div>
              ))
          )}
        </div>
      </div>
    </aside>
  );
}
