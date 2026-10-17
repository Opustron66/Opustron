import React, { useState } from "react";
import CitationPopover from "./CitationPopover";
import { factsAbout, hasEndedBy, isTrueAt } from "../services/api";

const fmt = (d, missing) =>
  d
    ? new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })
    : missing;

const words = (predicate) => predicate.replaceAll("_", " ");

// "Alice owns payments" reads as "owns: payments" on Alice's card and
// "who owns: Alice" on the payments card.
function groupFor(entityName, fact) {
  return fact.subject === entityName
    ? { label: words(fact.predicate), other: fact.object }
    : { label: `who ${words(fact.predicate)}`, other: fact.subject };
}

export default function EntityCard({ entity, allFacts, asOf }) {
  const [openCitation, setOpenCitation] = useState(null);

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

                  return (
                    <div
                      key={f.fact_id}
                      className={`fact-row ${isCurrent ? "fact-current" : ""} ${isSuperseded ? "fact-superseded" : ""}`}
                    >
                      <span className="fact-object">{other}</span>
                      <span className="fact-validity">
                        {fmt(f.valid_from, "unknown")} → {fmt(f.valid_to, "now")}
                      </span>
                      <button
                        className="citation-btn"
                        onClick={() =>
                          setOpenCitation(openCitation === f.fact_id ? null : f.fact_id)
                        }
                        aria-label={`Source: ${f.doc_id}`}
                      >
                        {f.doc_id}
                      </button>
                      {openCitation === f.fact_id && (
                        <CitationPopover
                          source={{ uri: f.doc_id, quote: f.quote }}
                          onClose={() => setOpenCitation(null)}
                        />
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
