import React, { useMemo, useState } from "react";
import { diffFacts } from "../services/api";
import { fmtDate, isoDay } from "../services/dates";
import { describeChange, humanizeFact } from "../services/humanize";
import FactChange from "./FactChange";

const SHOWN = 6;

function Group({ title, hint, kind, items, render }) {
  const [all, setAll] = useState(false);
  if (!items.length) return null;
  const shown = all ? items : items.slice(0, SHOWN);
  return (
    <div className={`diff-group diff-${kind}`}>
      <h3 className="diff-title">
        {title} <span className="sidebar-count">{items.length}</span>
      </h3>
      <p className="diff-hint">{hint}</p>
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

const plain = (f) => <span className="diff-plain">{humanizeFact(f)}</span>;

// Pick two dates and see what memory gained, lost and changed between them.
export default function DateDiff({ startDate, endDate, asOf, facts }) {
  // Default to the month leading up to the selected day, so the card opens with something to show.
  const [to, setTo] = useState(isoDay(asOf));
  const [from, setFrom] = useState(isoDay(new Date(Math.max(startDate, asOf - 30 * 86400000))));
  const { added, ended, changed } = useMemo(() => diffFacts(facts, from, to), [facts, from, to]);
  const empty = !added.length && !ended.length && !changed.length;
  const bounds = { min: isoDay(startDate), max: isoDay(endDate) };

  return (
    <section className="date-diff" aria-labelledby="date-diff-title">
      <div className="diff-head">
        <div>
          <h2 id="date-diff-title" className="diff-heading">Compare two dates</h2>
          <p className="diff-sub">See what Chronicle learned, forgot or updated between two days.</p>
        </div>
        <div className="diff-dates">
          <label className="diff-field">
            <span>From</span>
            <input type="date" value={from} {...bounds} onChange={(e) => e.target.value && setFrom(e.target.value)} />
          </label>
          <span className="diff-arrow" aria-hidden="true">→</span>
          <label className="diff-field">
            <span>To</span>
            <input type="date" value={to} {...bounds} onChange={(e) => e.target.value && setTo(e.target.value)} />
          </label>
        </div>
      </div>
      {empty ? (
        <p className="diff-empty">
          Nothing changed between {fmtDate(from)} and {fmtDate(to)}.
        </p>
      ) : (
        <div className="diff-groups">
          <Group title="Changed" hint="Something was replaced by something new." kind="changed" items={changed}
            render={({ before, after }) => (
              <>
                <FactChange before={before} after={after} />
                <span className="diff-plain">{describeChange(before, after)}</span>
              </>
            )} />
          <Group title="Added" hint="Became true in this period." kind="added" items={added} render={plain} />
          <Group title="Ended" hint="Stopped being true in this period." kind="ended" items={ended} render={plain} />
        </div>
      )}
    </section>
  );
}
