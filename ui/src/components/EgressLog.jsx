import React, { useState, useEffect } from "react";
import { getEgressLog, MOCK } from "../services/api";

const fmtTs = (ts) =>
  new Date(ts).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

const destination = (e) =>
  e.provider === "tavily" ? "Tavily search" : (e.model || e.provider || "unknown").split("/").pop();

export default function EgressLog() {
  const [entries, setEntries] = useState(MOCK.egressEntries);
  // "sample": never reached the server, showing made-up entries.
  // "offline": reached it before, still showing the last real entries.
  const [status, setStatus] = useState("sample");

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const data = await getEgressLog(30);
        if (!cancelled) {
          setEntries(data);
          setStatus("live");
        }
      } catch {
        if (!cancelled) setStatus((s) => (s === "sample" ? "sample" : "offline"));
      }
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <section className="egress-log">
      <header className="egress-header">
        <h2 className="egress-title">Egress Log</h2>
        <span className={`egress-status ${status}`}>
          {{ live: "● LIVE", offline: "offline", sample: "sample data" }[status]}
        </span>
        <span className="egress-subtitle">
          Everything that left this machine: model calls and web searches, as sent
        </span>
      </header>

      <div className="egress-entries">
        {entries.length === 0 && (
          <p className="egress-empty">Nothing has left this machine yet.</p>
        )}
        {entries.map((e, i) => (
          <div
            key={`${e.ts}-${i}`}
            className={`egress-entry ${e.redacted ? "egress-redacted" : "egress-clean"}${e.cached ? " egress-cached" : ""}`}
          >
            <span className="egress-ts">{fmtTs(e.ts)}</span>
            <span className="egress-provider">{destination(e)}</span>
            {e.cached && (
              <span className="egress-badge cached" title="Answered from the local cache; nothing was sent">
                ↺ cache · not sent
              </span>
            )}
            {e.redacted ? (
              <span className="egress-badge redacted">🔒 redacted</span>
            ) : (
              <span className="egress-badge clean">✓ clean</span>
            )}
            {e.pii_types?.length > 0 && (
              <span className="egress-pii-types">
                {e.pii_types.join(", ")}
              </span>
            )}
            {(e.prompt_tokens > 0 || e.completion_tokens > 0) && (
              <span className="egress-tokens">
                {e.prompt_tokens}↑ {e.completion_tokens}↓
              </span>
            )}
            <code className="egress-preview">{e.request_preview}</code>
          </div>
        ))}
      </div>
    </section>
  );
}
