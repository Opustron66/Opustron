import React, { useState, useEffect } from "react";
import Timeline from "./components/Timeline";
import EntityCard from "./components/EntityCard";
import ChatPanel from "./components/ChatPanel";
import EgressLog from "./components/EgressLog";
import { MOCK, getEntities, getFacts, getSpan } from "./services/api";
import "./styles.css";

const SAMPLE = {
  source: "sample",
  facts: MOCK.facts,
  entities: MOCK.entities,
  start: MOCK.corpusStart,
  end: MOCK.corpusEnd,
};

const utcDay = (iso) => new Date(`${iso.slice(0, 10)}T00:00:00Z`);

async function loadMemory() {
  const [facts, entities, span] = await Promise.all([getFacts(), getEntities(), getSpan()]);
  // Hermes notes are free text with no subject/object; the cards show claims.
  const claims = facts.filter((f) => f.subject && f.object);
  if (!claims.length || !span.start || !span.end) return { source: "empty", facts: [], entities: [] };
  return { source: "live", facts: claims, entities, start: utcDay(span.start), end: utcDay(span.end) };
}

export default function App() {
  const [memory, setMemory] = useState(SAMPLE);
  const [asOf, setAsOf] = useState(new Date("2026-05-10"));

  useEffect(() => {
    let cancelled = false;
    loadMemory()
      .then((loaded) => {
        if (cancelled) return;
        setMemory(loaded);
        if (loaded.source === "live") setAsOf(loaded.end);
      })
      .catch(() => {}); // memory server not running: keep the sample data
    return () => {
      cancelled = true;
    };
  }, []);

  const { facts, entities } = memory;
  const named = new Map(entities.map((e) => [e.name, e]));
  const mentions = new Map();
  facts.forEach((f) => [f.subject, f.object].forEach((n) => mentions.set(n, (mentions.get(n) || 0) + 1)));
  const cards = [...mentions.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([name]) => named.get(name) || { entity_id: name, name, entity_type: "unknown" });

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-logo">
          <span className="app-logo-mark">◈</span>
          <span className="app-title">Chronicle</span>
        </div>
        <span className="app-tagline">A personal agent whose memory keeps up</span>
        <div className="app-header-right">
          <span className={`app-corpus-label source-${memory.source}`}>
            {memory.source === "live" && `● Live memory · ${facts.length} facts`}
            {memory.source === "empty" && "● Live memory · no facts yet"}
            {memory.source === "sample" && "Sample data · memory server not running"}
          </span>
        </div>
      </header>

      {memory.source === "empty" ? (
        <div className="app-empty">
          The memory server is running but has no facts yet. Ingest a corpus with{" "}
          <code>python -m chronicle.ingest --corpus DIR --state DIR</code>, then reload.
        </div>
      ) : (
        <>
          <div className="app-timeline-section">
            <Timeline
              startDate={memory.start}
              endDate={memory.end}
              value={asOf}
              onChange={setAsOf}
              facts={facts}
            />
          </div>

          <div className="app-body">
            <aside className="app-sidebar">
              <h2 className="sidebar-title">
                Entities
                <span className="sidebar-count">{cards.length}</span>
              </h2>
              <div className="entity-list">
                {cards.map((entity) => (
                  <EntityCard key={entity.entity_id} entity={entity} allFacts={facts} asOf={asOf} />
                ))}
              </div>
            </aside>

            <main className="app-main">
              <ChatPanel asOf={asOf} />
            </main>
          </div>
        </>
      )}

      <footer className="app-footer">
        <EgressLog />
      </footer>
    </div>
  );
}
