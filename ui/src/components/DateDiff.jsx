import React, { useState } from "react";
import { compareFacts, factSentence, isoDay, formatDay } from "../services/memoryView";
import Icon from "./Icon";

export default function DateDiff({ facts, startDate, endDate }) {
  const [from, setFrom] = useState(isoDay(startDate));
  const [to, setTo] = useState(isoDay(endDate));
  const invalid = !from || !to || from > to;
  const diff = invalid ? { changed: [], added: [], ended: [] } : compareFacts(facts, from, to);
  return <section className="comparison-view">
    <div className="section-heading"><div><span className="eyebrow">BEFORE & AFTER</span><h2>See what changed.</h2><p>Compare the facts that were true on two different days.</p></div>
      <div className="comparison-dates"><label>From<input type="date" aria-label="Compare from" min={isoDay(startDate)} max={isoDay(endDate)} value={from} onChange={(e) => setFrom(e.target.value)} /></label><Icon name="arrow" /><label>To<input type="date" aria-label="Compare to" min={isoDay(startDate)} max={isoDay(endDate)} value={to} onChange={(e) => setTo(e.target.value)} /></label></div>
    </div>
    {invalid ? <p role="alert" className="empty-note">Choose an end date on or after the start date.</p> : <>
      <p className="comparison-caption">{formatDay(from)} <span>→</span> {formatDay(to)}</p>
      <div className="comparison-grid">
        {[['changed', 'Changed', 'A newer value took its place.'], ['added', 'Added', 'Became true in this period.'], ['ended', 'Ended', 'Was no longer true by the end.']].map(([key, title, help]) => <DiffGroup key={key} kind={key} title={title} help={help} rows={diff[key]} />)}
      </div>
    </>}
  </section>;
}

function DiffGroup({ kind, title, help, rows }) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? rows : rows.slice(0, 12);
  return <article className={`diff-group diff-${kind}`}><header><h3>{title}</h3><span className="count-pill">{rows.length}</span></header><p>{help}</p>
    <ul>{shown.map((row) => <li key={row.fact_id || row.before.fact_id}>{kind === 'changed' ? <><s>{factSentence(row.before)}</s><span>{factSentence(row.after)}</span></> : factSentence(row)}</li>)}</ul>
    {!rows.length && <div className="diff-none">No {title.toLowerCase()} facts</div>}
    {rows.length > 12 && <button className="text-button" onClick={() => setExpanded(!expanded)}>{expanded ? 'Show fewer' : `Show all ${rows.length}`}</button>}
  </article>;
}
