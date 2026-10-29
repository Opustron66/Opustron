import React, { useMemo, useState } from "react";
import { diffFacts } from "../services/api";
import FactChange from "./FactChange";

const SHOWN = 8;
const iso = (d) => d.toISOString().slice(0, 10);
const label = (f) => `${f.subject} · ${f.predicate.replace(/_/g, " ")}: ${f.object}`;

function Group({ title, kind, items, render }) {
  const [all, setAll] = useState(false);
  if (!items.length) return null;
  const shown = all ? items : items.slice(0, SHOWN);
  return (
    <div className={`diff-group diff-${kind}`}>
      <h3 className="diff-title">
        {title} <span className="sidebar-count">{items.length}</span>
      </h3>
      <ul>
        {shown.map((item, i) => (
          <li key={i}>{render(item)}</li>
        ))}
      </ul>
      {items.length > SHOWN && (
        <button className="diff-more" onClick={() => setAll(!all)}>
          {all ? "Show fewer" : `Show all ${items.length}`}
        </button>
      )}
    </div>
  );
}

// Pick two dates and see what memory gained, lost and changed between them.
export default function DateDiff({ startDate, endDate, asOf, facts }) {
  const [from, setFrom] = useState(iso(asOf));
  const [to, setTo] = useState(iso(endDate));
  const { added, ended, changed } = useMemo(() => diffFacts(facts, from, to), [facts, from, to]);
  const empty = !added.length && !ended.length && !changed.length;

  return (
    <details className="date-diff">
      <summary>Compare two dates</summary>
      <div className="diff-dates">
        <label>
          From{" "}
          <input type="date" value={from} min={iso(startDate)} max={iso(endDate)}
            onChange={(e) => e.target.value && setFrom(e.target.value)} />
        </label>
        <label>
          To{" "}
          <input type="date" value={to} min={iso(startDate)} max={iso(endDate)}
            onChange={(e) => e.target.value && setTo(e.target.value)} />
        </label>
      </div>
      {empty ? (
        <p className="diff-empty">Nothing changed between these dates.</p>
      ) : (
        <div className="diff-groups">
          <Group title="Changed" kind="changed" items={changed}
            render={({ before, after }) => <FactChange before={before} after={after} />} />
          <Group title="Added" kind="added" items={added} render={label} />
          <Group title="Ended" kind="ended" items={ended} render={label} />
        </div>
      )}
    </details>
  );
}
