import React, { useState, useRef, useEffect } from "react";
import { ask, replacedFacts } from "../services/api";
import FactChange from "./FactChange";

const fmt = (d) =>
  new Date(d).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  });

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
          Answered as of <strong>{fmt(message.asOf)}</strong>: only facts known by then were used.
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

export default function ChatPanel({ asOf, facts = [] }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: `Chronicle is ready. I'm answering as of **${fmt(asOf)}**. Ask me anything about the corpus — who owned what, when things changed, or what happened on a specific date.`,
      ts: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Update the system message when asOf changes
  useEffect(() => {
    setMessages((prev) => {
      const updated = [...prev];
      updated[0] = {
        ...updated[0],
        content: `Chronicle is ready. I'm answering as of **${fmt(asOf)}**. Ask me anything about the corpus.`,
      };
      return updated;
    });
  }, [asOf]);

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: q, ts: Date.now() },
    ]);
    setLoading(true);
    try {
      const data = await ask(q, asOf.toISOString().slice(0, 10));
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          citations: data.citations,
          support: data.support,
          asOf: data.as_of,
          refused: data.refused,
          ts: Date.now(),
        },
      ]);
    } catch {
      // A failed request must never become an invented corpus answer.
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Unable to get an answer. Check that the memory server is running and its model credentials are configured, then try again.",
          citations: [],
          ts: Date.now(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <section className="chat-panel">
      <header className="chat-header">
        <h2 className="chat-title">Ask Chronicle</h2>
        <span className="chat-asof">as of {fmt(asOf)}</span>
      </header>

      <div className="chat-messages">
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
          <div className="chat-message chat-assistant">
            <span className="chat-thinking">Thinking…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          rows={2}
          placeholder="Who owned payments on 3 May? What changed after 15 May?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
        />
        <button className="chat-send" onClick={send} disabled={loading || !input.trim()}>
          Ask
        </button>
      </div>
    </section>
  );
}
