import React, { useMemo } from "react";
import { isTrueAt } from "../services/api";
import { formatDay, isoDay } from "../services/memoryView";
import Icon from "./Icon";

const DAY = 86400000;
export default function Timeline({ startDate, endDate, value, onChange, facts = [] }) {
  const totalDays = Math.max(0, Math.round((endDate - startDate) / DAY));
  const currentDay = Math.min(totalDays, Math.max(0, Math.round((value - startDate) / DAY)));
  const pct = totalDays ? currentDay / totalDays * 100 : 0;
  const ticks = useMemo(() => [...new Set(facts.flatMap((f) => [f.valid_from, f.valid_to]).filter(Boolean).map((d) => d.slice(0, 10)))].sort().filter((d) => new Date(d) >= startDate && new Date(d) <= endDate), [facts, startDate, endDate]);
  const changeDay = (offset) => onChange(new Date(startDate.getTime() + Math.min(totalDays, Math.max(0, offset)) * DAY));
  return <div className="timeline-wrap">
    <div className="timeline-header"><div className="timeline-heading"><Icon name="clock" size={18} /><span className="timeline-label">Memory Time Machine</span><span className="timeline-helper">A different day. A different perspective.</span></div><div className="timeline-date-controls"><button aria-label="Previous day" className="icon-button" disabled={!currentDay} onClick={() => changeDay(currentDay - 1)}>←</button><label className="timeline-date"><span>{formatDay(value)}</span><input type="date" aria-label="Choose exact memory date" min={isoDay(startDate)} max={isoDay(endDate)} value={isoDay(value)} onChange={(e) => { if (!e.target.value) return; const date = new Date(`${e.target.value}T00:00:00Z`); if (date >= startDate && date <= endDate) onChange(date); }} /></label><button aria-label="Next day" className="icon-button" disabled={currentDay >= totalDays} onClick={() => changeDay(currentDay + 1)}>→</button></div></div>
    <div className="timeline-track-wrap"><span className="timeline-bound">{formatDay(startDate)}</span><div className="timeline-track"><div className="timeline-fill" style={{ width: `${pct}%` }} />{ticks.filter((_, i) => i % Math.max(1, Math.ceil(ticks.length / 18)) === 0).map((date) => <span key={date} className="timeline-tick" title={formatDay(date)} style={{ left: `${totalDays ? (new Date(date) - startDate) / (endDate - startDate) * 100 : 0}%` }} />)}<input type="range" min={0} max={totalDays} value={currentDay} aria-label="Select date in memory" aria-valuetext={formatDay(value)} onChange={(e) => changeDay(Number(e.target.value))} className="timeline-slider" /></div><span className="timeline-bound">{formatDay(endDate)}</span></div>
    <div className="timeline-facts" aria-hidden="true">{facts.slice(0, 120).map((f) => <span key={f.fact_id} className={`timeline-fact-bar ${isTrueAt(f, value) ? 'active' : 'inactive'}`} title={`${f.subject} — ${f.predicate}: ${f.object}`} />)}</div>
  </div>;
}