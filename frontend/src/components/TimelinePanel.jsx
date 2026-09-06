import React from "react";
import EventGraphPanel from "./EventGraphPanel.jsx";

export default function TimelinePanel({ data, eventGraph }) {
  const { timeline, conflicts, entity_links: entityLinks } = data;

  return (
    <section className="panel active">
      <header className="panel-head">
        <h1>Timeline &amp; entity links</h1>
        <p>
          Events in chronological order, with any timestamp conflicts surfaced
          separately &mdash; never silently resolved.
        </p>
      </header>

      {conflicts.length > 0 && (
        <div className="conflicts-box">
          <h3>Timestamp conflicts detected</h3>
          {conflicts.map((c, i) => (
            <p key={i}>
              User <b>{c.user}</b> at {c.timestamp}: {c.reason} (
              {c.conflicting_ips.join(", ")})
            </p>
          ))}
        </div>
      )}

      <div className="timeline-list">
        {timeline.map((e) => (
          <div className="tl-row" key={e.event_id}>
            <div className="tl-time">
              {e.timestamp} &middot; {e.event_id}
            </div>
            <div className="tl-type">
              {e.event_type} &mdash; {e.user}@{e.device}
            </div>
            <div className="tl-desc">{e.description}</div>
          </div>
        ))}
      </div>

      {eventGraph && (
        <>
          <h2 className="split-title" style={{ marginTop: "2rem" }}>
            Event relation graph
          </h2>
          <p className="rail-note" style={{ marginBottom: "1rem" }}>
            Who touched what, and how much. Each dot is an entity from the
            events above; a line means the two showed up in the same event.
          </p>
          <EventGraphPanel graph={eventGraph} />
        </>
      )}

      <h2 className="split-title" style={{ marginTop: "2rem" }}>
        Entity links <span className="tag tag-baseline">text view</span>
      </h2>
      <div className="entity-grid">
        {Object.entries(entityLinks).map(([entity, ids]) => (
          <div className="entity-card" key={entity}>
            <div className="ename">{entity}</div>
            <div className="eids">{ids.join(", ")}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
