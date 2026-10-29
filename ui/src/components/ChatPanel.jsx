import React, { useState, useRef, useEffect } from "react";
import { ask, replacedFacts } from "../services/api";
import { fmtDate } from "../services/dates";
import FactChange from "./FactChange";
import Icon from "./Icon";

// Published corpus_a/questions/questions.jsonl: fact-031,
// fresh-quillon-launch-date, attrib-eval-owners, asof-backfill-window.
const EXAMPLES = [
  "What is the GitLab project path for Atlas?",
  "What is the current internal launch target date for Quillon v2? Answer with the date only.",
  "Who owns Beacon's eval framework, and who owns the evaluator metric decision?",
  "As of 2026-05-20, what was the default cold-start ingest backfill window?",
];

const CHATS_KEY = "chronicle.chats";
const CURRENT_KEY = "chronicle.chats.current";

// The user's own calendar day: "what did I ask yesterday" means their yesterday.
const localDay = (ts) => {
  const d = new Date(ts);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

// Stored as { "YYYY-MM-DD": [{ id, startedAt, messages }] }, keyed by the day each chat began.
function loadSessions() {
  try {
    const byDay = JSON.parse(localStorage.getItem(CHATS_KEY) || "{}");
    return Object.values(byDay).flat().filter((s) => s && s.id && Array.isArray(s.messages));
  } catch {
    return [];
  }
}

function saveSessions(sessions) {
  const byDay = {};
  sessions
    .filter((s) => s.messages.length)
    .forEach((s) => (byDay[localDay(s.startedAt)] ||= []).push(s));
  try {
    localStorage.setItem(CHATS_KEY, JSON.stringify(byDay));
  } catch {}
}

const newSession = () => ({ id: `chat-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, startedAt: Date.now(), messages: [] });

function initialState() {
  const sessions = loadSessions();
  let currentId = null;
  try {
    currentId = localStorage.getItem(CURRENT_KEY);
  } catch {}
  if (sessions.some((s) => s.id === currentId)) return { sessions, currentId };
  const fresh = newSession();
  return { sessions: [...sessions, fresh], currentId: fresh.id };
}

function dayHeading(day) {
  const today = localDay(Date.now());
  const yesterday = localDay(Date.now() - 86400000);
  if (day === today) return "Today";
  if (day === yesterday) return "Yesterday";
  return new Date(`${day}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

// Answers quote ingested documents, so content is untrusted: build React nodes, never HTML.
function renderInline(text) {
  return text.split("\n").map((line, i) => (
    <React.Fragment key={i}>
      {i > 0 && <br />}
      {line.split(/\*\*(.+?)\*\*/g).map((part, j) => (j % 2 ? <strong key={j}>{part}</strong> : part))}
    </React.Fragment>
  ));
}

// The evidence behind an answer: verified quotes, the as-of date and any fact it replaced.
function WhyPanel({ message, facts }) {
  const replaced = replacedFacts(facts, (message.citations || []).map((c) => c.doc_id));
  if (!message.support?.length && !message.asOf && !replaced.length) return null;
  return (
    <details className="chat-why">
      <summary>Why?</summary>
      {message.asOf && (
        <p className="why-asof">
          Answered as of <strong>{fmtDate(message.asOf)}</strong>: only facts known by then were used.
        </p>
      )}
      {message.support?.length > 0 && (
        <ul className="why-quotes">
          {message.support.map((s, i) => (
            <li key={i}>
              <blockquote className="citation-quote">"{s.quote}"</blockquote>
              {s.doc_id && <span className="citation-chip">{s.doc_id}</span>}
            </li>
          ))}
        </ul>
      )}
      {replaced.length > 0 && (
        <div className="why-replaced">
          <span className="why-label">Replaced</span>
          {replaced.map(({ before, after }) => (
            <FactChange key={before.fact_id} before={before} after={after} />
          ))}
        </div>
      )}
    </details>
  );
}

function History({ sessions, currentId, onOpen }) {
  const past = sessions.filter((s) => s.messages.length).sort((a, b) => b.startedAt - a.startedAt);
  if (!past.length) return <p className="chat-history-empty">No past chats yet. Questions you ask are saved here, in this browser only.</p>;
  const days = [];
  past.forEach((s) => {
    const day = localDay(s.startedAt);
    if (days.at(-1)?.day !== day) days.push({ day, items: [] });
    days.at(-1).items.push(s);
  });
  return (
    <nav className="chat-history" aria-label="Past chats">
      {days.map(({ day, items }) => (
        <section key={day}>
          <h3 className="chat-history-day">{dayHeading(day)}</h3>
          <ul>
            {items.map((s) => {
              const first = s.messages.find((m) => m.role === "user")?.content || "Untitled chat";
              const asked = s.messages.filter((m) => m.role === "user").length;
              return (
                <li key={s.id}>
                  <button
                    type="button"
                    className={`chat-history-item${s.id === currentId ? " current" : ""}`}
                    aria-current={s.id === currentId ? "true" : undefined}
                    onClick={() => onOpen(s.id)}
                  >
                    <span className="chat-history-title">{first}</span>
                    <span className="chat-history-meta">
                      {new Date(s.startedAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
                      {" · "}
                      {asked} {asked === 1 ? "question" : "questions"}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </nav>
  );
}

export default function ChatPanel({ asOf, facts = [], enabled = true, onExplore = () => {} }) {
  const [{ sessions, currentId }, setState] = useState(initialState);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [showHistory, setShowHistory] = useState(false);
  const bottomRef = useRef(null);

  const current = sessions.find((s) => s.id === currentId);
  const messages = current?.messages || [];
  const pastCount = sessions.filter((s) => s.messages.length).length;

  useEffect(() => {
    if (!loading) { setElapsed(0); return; }
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [loading]);

  useEffect(() => {
    if (messages.length || loading) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, loading]);

  useEffect(() => {
    saveSessions(sessions);
    try {
      localStorage.setItem(CURRENT_KEY, currentId);
    } catch {}
  }, [sessions, currentId]);

  if (!enabled) return (
    <section className="chat-panel chat-preview">
      <header className="chat-header"><h2 className="chat-title">Ask Chronicle</h2><span className="mode-badge">Browse-only demo</span></header>
      <div className="chat-preview-body">
        <span className="assistant-symbol"><Icon name="memory" size={28} /></span>
        <span className="eyebrow">START WITH A LITTLE CURIOSITY</span>
        <h2>Good questions.<br />Remembered details.</h2>
        <p>Live answers are paused in this public demo. There’s still a whole memory to explore.</p>
        <div className="explore-prompts">
          <button onClick={() => onExplore('owns')}><Icon name="person" /><span><strong>Who owns what?</strong><small>Explore owners and project leads</small></span><Icon name="arrow" size={16} /></button>
          <button onClick={() => onExplore('deadline')}><Icon name="clock" /><span><strong>What’s coming up?</strong><small>Find dates, plans, and deadlines</small></span><Icon name="arrow" size={16} /></button>
          <button onClick={() => onExplore('history')}><Icon name="compare" /><span><strong>What changed along the way?</strong><small>Look back at earlier facts</small></span><Icon name="arrow" size={16} /></button>
        </div>
        <div className="browse-reassurance"><Icon name="shield" size={15} /><span>Explore saved evidence. No live AI requests.</span></div>
      </div>
      <div className="chat-input-row"><textarea className="chat-input" rows={1} aria-label="Chat unavailable in browse-only demo" placeholder="Live chat is paused in this demo" disabled /><button className="chat-send" aria-label="Send question" disabled><Icon name="arrow" /></button></div>
    </section>
  );

  // Writes go to the chat the question was asked in, even if the user has since switched.
  const append = (id, message) =>
    setState((st) => ({
      ...st,
      sessions: st.sessions.map((s) =>
        s.id === id
          ? { ...s, startedAt: s.messages.length ? s.startedAt : message.ts, messages: [...s.messages, message] }
          : s
      ),
    }));

  const openSession = (id) => {
    setState((st) => ({ sessions: st.sessions.filter((s) => s.messages.length || s.id === id), currentId: id }));
    setShowHistory(false);
  };

  const startNew = () => {
    setShowHistory(false);
    if (!messages.length) return;
    const fresh = newSession();
    setState((st) => ({ sessions: [...st.sessions, fresh], currentId: fresh.id }));
  };

  const send = async (text) => {
    const q = text.trim();
    if (!enabled || !q || loading) return;
    const id = currentId;
    setInput("");
    append(id, { role: "user", content: q, ts: Date.now() });
    setLoading(true);
    try {
      const data = await ask(q, asOf.toISOString().slice(0, 10));
      append(id, {
        role: "assistant",
        content: data.answer,
        citations: data.citations,
        support: data.support,
        asOf: data.as_of,
        refused: data.refused,
        ts: Date.now(),
      });
    } catch (error) {
      // A failed request must never become an invented corpus answer.
      append(id, {
        role: "assistant",
        content: error.status === 503
          ? "Live chat is unavailable or its demo budget has been used. You can still explore saved facts and sources."
          : "Unable to get an answer. Check that the memory server is running and its model credentials are configured, then try again.",
        citations: [],
        ts: Date.now(),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  return (
    <section className="chat-panel">
      <header className="chat-header">
        <h2 className="chat-title">Ask Chronicle</h2>
        <div className="chat-header-actions">
          <span className="chat-asof">as of {fmtDate(asOf)}</span>
          <button
            type="button"
            className="chat-header-btn"
            aria-expanded={showHistory}
            onClick={() => setShowHistory(!showHistory)}
          >
            History{pastCount > 0 && <span className="sidebar-count">{pastCount}</span>}
          </button>
          <button type="button" className="chat-header-btn" onClick={startNew} disabled={!messages.length}>
            New chat
          </button>
        </div>
      </header>

      {showHistory && (
        <div className="chat-history-drawer">
          <History sessions={sessions} currentId={currentId} onOpen={openSession} />
        </div>
      )}

      <div className="chat-messages">
        {messages.length === 0 && !loading && (
          <div className="chat-empty">
            <p className="chat-empty-title">What would you like to remember?</p>
            <p className="chat-empty-hint">
              Chronicle answers from memory as it stood on <strong>{fmtDate(asOf)}</strong>. Move the Time Machine to
              ask about another day. Try a question from NVIDIA Corpus A:
            </p>
            <div className="chat-examples">
              {EXAMPLES.map((q) => (
                <button key={q} type="button" className="chat-example" onClick={() => send(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-message chat-${m.role}${m.refused ? " chat-refusal" : ""}`}>
            {m.refused && <span className="chat-refusal-label">Not in memory</span>}
            <div className="chat-content">{renderInline(m.content)}</div>
            {m.citations?.length > 0 && (
              <div className="chat-citations">
                {m.citations.map((c) => (
                  <span key={c.doc_id} className="citation-chip">
                    {c.doc_id}
                  </span>
                ))}
              </div>
            )}
            {m.role === "assistant" && !m.refused && <WhyPanel message={m} facts={facts} />}
          </div>
        ))}
        {loading && (
          <div className="chat-message chat-assistant" role="status">
            <span className="chat-thinking">Generating an answer… {elapsed}s{elapsed >= 15 && <><br />Still waiting for the complete answer. It may involve multiple evidence checks.</>}</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          rows={2}
          aria-label="Ask a question"
          placeholder="Who owned payments on 3 May? What changed after 15 May?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
        />
        <button className="chat-send" onClick={() => send(input)} disabled={loading || !input.trim()}>
          Ask
        </button>
      </div>
    </section>
  );
}
