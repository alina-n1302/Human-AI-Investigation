import React from "react";

const TAB_DEFS = [
  { id: "evidence", label: "Evidence" },
  { id: "timeline", label: "Timeline & Graph" },
  { id: "hypotheses", label: "Hypotheses" },
  { id: "robustness", label: "Robustness" },
  { id: "decision", label: "Investigator decision" },
];

export default function Tabs({ active, onChange }) {
  return (
    <nav className="tabs">
      {TAB_DEFS.map((tab) => (
        <button
          key={tab.id}
          className={`tab${active === tab.id ? " active" : ""}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
