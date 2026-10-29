import React, { useState, useEffect } from "react";
import { getEgressLog } from "../services/api";
import Icon from "./Icon";

const fmtTs = (ts) =>
  new Date(ts).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

const destination = (e) =>
  e.provider === "tavily" ? "Tavily search" : (e.model || e.provider || "unknown").split("/").pop();

export default function EgressLog() {
  const [entries, setEntries] = useState([]);
  const [status, setStatus] = useState("connecting");

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
        if (!cancelled) setStatus("offline");
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
    <details className="egress-log">
      <summary className="egress-header">
        <Icon name="activity" size={17} />
        <h2 className="egress-title">Egress Log</h2>
        <span className={`egress-status ${status}`}>
          {{ live: "● LIVE", offline: "offline", connecting: "connecting" }[status]}
        </span>
        <span className="egress-subtitle">
          Everything that left this machine: model calls and web searches, as sent
        </span>
        <span className="egress-expand">{entries.length} entries · Expand</span>
      </summary>

      <div className="egress-entries">
        {entries.length === 0 && (
          <p className="egress-empty">{status === 'live' ? 'Nothing has left this machine yet.' : 'The activity log is not connected. No sample requests are shown.'}</p>
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
    </details>
  );
}
