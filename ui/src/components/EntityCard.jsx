import React, { useState } from "react";
import { factsAbout, hasEndedBy, isTrueAt } from "../services/api";
import { fmtDate } from "../services/dates";
import { describeStatusAt, describeValidity, humanizeFact } from "../services/humanize";

const fmt = (d, missing) => (d ? fmtDate(d) : missing);

const words = (predicate) => predicate.replace(/^attr:/, "").replaceAll("_", " ");

// "Alice owns payments" reads as "owns: payments" on Alice's card and
// "who owns: Alice" on the payments card.
function groupFor(entityName, fact) {
  return fact.subject === entityName
    ? { label: words(fact.predicate), other: fact.object }
    : { label: `who ${words(fact.predicate)}`, other: fact.subject };
}

export default function EntityCard({ entity, allFacts, asOf }) {
  const [open, setOpen] = useState(null);

  const groups = {};
  factsAbout(allFacts, entity.name).forEach((f) => {
    const { label, other } = groupFor(entity.name, f);
    (groups[label] ||= []).push({ fact: f, other });
  });

  return (
    <article className="entity-card">
      <header className="entity-card-header">
        <span className="entity-type-badge">{entity.entity_type}</span>
        <h3 className="entity-name">{entity.name}</h3>
      </header>

      <div className="entity-facts">
        {Object.entries(groups).map(([label, rows]) => {
          const sorted = [...rows].sort(
            (a, b) => new Date(a.fact.valid_from || 0) - new Date(b.fact.valid_from || 0)
          );
          return (
            <div key={label} className="entity-predicate-group">
              <span className="entity-predicate">{label}</span>
              <div className="entity-values">
                {sorted.map(({ fact: f, other }) => {
                  const isCurrent = isTrueAt(f, asOf);
                  const isSuperseded = hasEndedBy(f, asOf);
                  const expanded = open === f.fact_id;
                  const explainId = `explain-${f.fact_id}`;

                  return (
                    <div
                      key={f.fact_id}
                      className={`fact-row ${isCurrent ? "fact-current" : ""} ${isSuperseded ? "fact-superseded" : ""}`}
                    >
                      <button
                        type="button"
                        className="fact-toggle"
                        aria-expanded={expanded}
                        aria-controls={explainId}
                        title="What does this mean?"
                        onClick={() => setOpen(expanded ? null : f.fact_id)}
                      >
                        <span className="fact-object">{other}</span>
                        <span className="fact-validity">
                          {fmt(f.valid_from, "unknown")} → {fmt(f.valid_to, "now")}
                        </span>
                        <span className="fact-chevron" aria-hidden="true">{expanded ? "−" : "+"}</span>
                      </button>
                      {expanded && (
                        <div className="fact-explain" id={explainId}>
                          <p>{humanizeFact(f)}</p>
                          <p className="fact-explain-dates">
                            {describeValidity(f)} {describeStatusAt(f, asOf)}
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}
