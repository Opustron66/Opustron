import React, { useState, useEffect } from "react";
import Timeline from "./components/Timeline";
import EntityCard from "./components/EntityCard";
import ChatPanel from "./components/ChatPanel";
import EgressLog from "./components/EgressLog";
import DateDiff from "./components/DateDiff";
import { MOCK, getEntities, getFacts, getSpan } from "./services/api";
import { clampDate, todayUTC, utcDay } from "./services/dates";
import "./styles.css";

const SAMPLE = {
  source: "sample",
  facts: MOCK.facts,
  entities: MOCK.entities,
  start: MOCK.corpusStart,
  end: MOCK.corpusEnd,
};

// Facts valid far into the future must not stretch the time machine past today.
const lastDay = (end) => (end > todayUTC() ? todayUTC() : end);

async function loadMemory() {
  const [facts, entities, span] = await Promise.all([getFacts(), getEntities(), getSpan()]);
  // Hermes notes are free text with no subject/object; the cards show claims.
  const claims = facts.filter((f) => f.subject && f.object);
  if (!claims.length || !span.start || !span.end) return { source: "empty", facts: [], entities: [] };
  return { source: "live", facts: claims, entities, start: utcDay(span.start), end: lastDay(utcDay(span.end)) };
}

const THEME_KEY = "chronicle.theme";

function initialTheme() {
  const set = document.documentElement.dataset.theme;
  if (set === "light" || set === "dark") return set;
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {}
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

// An elephant (it never forgets) with a small neural network in its head.
function ElephantLogo() {
  return (
    <svg className="app-logo-mark" viewBox="0 0 40 32" width="34" height="27" aria-hidden="true">
      <g fill="currentColor">
        <path d="M17 7.5C23 4 33 5 36.5 11.5c1.8 3.4 1.6 8-.2 11.2V29a1 1 0 0 1-1 1h-2.6a1 1 0 0 1-1-1v-3.6h-8V29a1 1 0 0 1-1 1h-2.6a1 1 0 0 1-1-1v-5.2C17 21 16 18 17 7.5z" />
        <circle cx="13.5" cy="12.5" r="9" />
        <path d="M6.2 17.5c-2.4 3.4-2.6 8.2.3 10.6 1.6 1.3 3.8.6 3.6-1.3" fill="none" stroke="currentColor" strokeWidth="3.4" strokeLinecap="round" />
        <path d="M36.6 13.5c1.6.8 2.4 2.4 2.1 4.2" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </g>
      <path className="app-logo-ear" d="M17.5 6.5c5 .2 7.5 4.6 6.3 9.4-.9 3.5-3.9 4.8-6.6 3.4" fill="none" strokeWidth="1.4" strokeLinecap="round" />
      <g className="app-logo-net" strokeWidth="1" strokeLinecap="round">
        <path d="M8 8.5L12 6.2L15 10L11.5 12.5Z M12 6.2L11.5 12.5 M8 8.5L6.5 12" fill="none" />
        <circle cx="8" cy="8.5" r="1.4" />
        <circle cx="12" cy="6.2" r="1.4" />
        <circle cx="15" cy="10" r="1.2" />
        <circle cx="11.5" cy="12.5" r="1.4" />
        <circle cx="6.5" cy="12" r="1" />
      </g>
      <circle className="app-logo-eye" cx="9" cy="16" r="1" />
    </svg>
  );
}

function ThemeToggle({ theme, onToggle }) {
  const next = theme === "dark" ? "light" : "dark";
  return (
    <button type="button" className="theme-toggle" onClick={onToggle} aria-label={`Switch to ${next} mode`} title={`Switch to ${next} mode`}>
      {theme === "dark" ? (
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <circle cx="10" cy="10" r="3.6" fill="currentColor" />
          <path d="M10 1.8v2.4M10 15.8v2.4M1.8 10h2.4M15.8 10h2.4M4.2 4.2l1.7 1.7M14.1 14.1l1.7 1.7M4.2 15.8l1.7-1.7M14.1 5.9l1.7-1.7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      ) : (
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <path d="M16.5 12.6A7 7 0 0 1 7.4 3.5a7 7 0 1 0 9.1 9.1z" fill="currentColor" />
        </svg>
      )}
    </button>
  );
}

export default function App() {
  const [memory, setMemory] = useState(SAMPLE);
  const [asOf, setAsOf] = useState(new Date("2026-05-10"));
  const [query, setQuery] = useState("");
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {}
  }, [theme]);

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
  const needle = query.trim().toLowerCase();
  const shown = needle ? cards.filter((c) => c.name.toLowerCase().includes(needle)) : cards;
  const changeAsOf = (d) => setAsOf(clampDate(d, memory.start, memory.end));

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-logo">
          <ElephantLogo />
          <span className="app-title">Chronicle</span>
        </div>
        <span className="app-tagline">A personal agent whose memory keeps up</span>
        <div className="app-header-right">
          <span className={`app-corpus-label source-${memory.source}`}>
            {memory.source === "live" && `● Live memory · ${facts.length} facts`}
            {memory.source === "empty" && "● Live memory · no facts yet"}
            {memory.source === "sample" && "Sample data · memory server not running"}
          </span>
          <ThemeToggle theme={theme} onToggle={() => setTheme(theme === "dark" ? "light" : "dark")} />
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
            <Timeline startDate={memory.start} endDate={memory.end} value={asOf} onChange={changeAsOf} />
            <DateDiff key={memory.source} startDate={memory.start} endDate={memory.end} asOf={asOf} facts={facts} />
          </div>

          <div className="app-body">
            <aside className="app-sidebar">
              <h2 className="sidebar-title">
                Entities
                <span className="sidebar-count">{needle ? `${shown.length} / ${cards.length}` : cards.length}</span>
              </h2>
              <div className="entity-search">
                <svg viewBox="0 0 16 16" aria-hidden="true">
                  <circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <input
                  type="search"
                  aria-label="Search entities"
                  placeholder="Search people, projects…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <div className="entity-list">
                {shown.length === 0 && <p className="entity-none">No entity found for “{query.trim()}”.</p>}
                {shown.map((entity) => (
                  <EntityCard key={entity.entity_id} entity={entity} allFacts={facts} asOf={asOf} />
                ))}
              </div>
            </aside>

            <main className="app-main">
              <ChatPanel asOf={asOf} facts={facts} />
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
