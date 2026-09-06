import React, { useMemo, useState } from "react";

const TYPE_COLOR = {
  user: "var(--amber)",
  device: "var(--cyan)",
  ip: "var(--clay)",
  destination: "var(--moss)",
  process: "var(--text-dim)",
};

const TYPE_LABEL = {
  user: "User",
  device: "Device",
  ip: "Source IP",
  destination: "Destination",
  process: "Process",
};

const SIZE = 480;
const CENTER = SIZE / 2;
const RADIUS = 190;

function layout(nodes) {
  const n = Math.max(nodes.length, 1);
  return nodes.map((node, i) => {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
    return {
      ...node,
      x: CENTER + RADIUS * Math.cos(angle),
      y: CENTER + RADIUS * Math.sin(angle),
    };
  });
}

export default function EventGraphPanel({ graph }) {
  const [selected, setSelected] = useState(null);
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];

  const positioned = useMemo(() => layout(nodes), [nodes]);
  const byId = useMemo(
    () => Object.fromEntries(positioned.map((n) => [n.id, n])),
    [positioned],
  );

  const maxWeight = Math.max(1, ...edges.map((e) => e.weight));
  const maxCount = Math.max(1, ...nodes.map((n) => n.event_count));

  const neighborIds = useMemo(() => {
    if (!selected) return null;
    const ids = new Set([selected]);
    edges.forEach((e) => {
      if (e.source === selected) ids.add(e.target);
      if (e.target === selected) ids.add(e.source);
    });
    return ids;
  }, [selected, edges]);

  if (nodes.length === 0) {
    return <p className="rail-note">No entities to graph for this case.</p>;
  }

  return (
    <div className="graph-wrap">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="graph-svg"
        role="img"
        aria-label="Entity relationship graph: lines connect entities that appeared together in the same event"
      >
        {edges.map((e, i) => {
          const a = byId[e.source];
          const b = byId[e.target];
          if (!a || !b) return null;
          const dim =
            neighborIds &&
            !(neighborIds.has(e.source) && neighborIds.has(e.target));
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              className={`graph-edge${dim ? " graph-edge-dim" : ""}`}
              strokeWidth={1 + (e.weight / maxWeight) * 4}
            >
              <title>{`${e.source} ↔ ${e.target} — ${e.weight} shared event(s): ${e.event_ids.join(", ")}`}</title>
            </line>
          );
        })}

        {positioned.map((n) => {
          const r = 7 + (n.event_count / maxCount) * 11;
          const dim = neighborIds && !neighborIds.has(n.id);
          const active = selected === n.id;
          return (
            <g
              key={n.id}
              transform={`translate(${n.x}, ${n.y})`}
              className={`graph-node${dim ? " graph-node-dim" : ""}${active ? " graph-node-active" : ""}`}
              onClick={() => setSelected(active ? null : n.id)}
            >
              <circle r={r} fill={TYPE_COLOR[n.type] || "var(--text-dim)"} />
              <title>{`${n.label} (${TYPE_LABEL[n.type] || n.type}) — appears in ${n.event_count} event(s)`}</title>
              <text y={r + 13} textAnchor="middle" className="graph-label">
                {n.label}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="graph-legend">
        <div className="legend-title">Entity type</div>
        {Object.keys(TYPE_LABEL).map((type) => (
          <div className="legend-item" key={type}>
            <span
              className="legend-dot"
              style={{ background: TYPE_COLOR[type] }}
            />
            {TYPE_LABEL[type]}
          </div>
        ))}
        <p className="rail-note graph-help">
          Click an entity to highlight only what it directly co-occurred with.
          Line thickness and node size both scale with how often two entities
          appear together &mdash; hover either for the exact shared event IDs.
          Layout is a fixed circle, not a physics simulation, so the same case
          always draws the same way.
        </p>
        {selected && (
          <button
            type="button"
            className="graph-clear"
            onClick={() => setSelected(null)}
          >
            Clear selection ({selected})
          </button>
        )}
      </div>
    </div>
  );
}
