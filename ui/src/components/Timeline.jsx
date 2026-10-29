import React, { useMemo, useRef, useState } from "react";
import { clampDate, fmtDate, isoDay, parseDay, snapStops } from "../services/dates";

function DateField({ value, min, max, onChange }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  const [error, setError] = useState(false);
  const cancelled = useRef(false);

  const open = () => {
    cancelled.current = false;
    setText(isoDay(value));
    setError(false);
    setEditing(true);
  };
  const commit = () => {
    const d = parseDay(text);
    if (!d) return setError(true);
    onChange(clampDate(d, min, max));
    setEditing(false);
  };

  if (!editing) {
    return (
      <button type="button" className="timeline-date" onClick={open} title="Click to type an exact date">
        {fmtDate(value)}
        <svg className="timeline-date-icon" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M11.5 2.5l2 2L6 12H4v-2z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
        </svg>
      </button>
    );
  }
  return (
    <span className="timeline-date-edit">
      {error && <span className="timeline-date-error" role="alert">Try a date like 2026-05-12 or 12 May 2026</span>}
      <input
        onFocus={(e) => e.target.select()}
        className={`timeline-date-input${error ? " invalid" : ""}`}
        aria-label="Type a date"
        aria-invalid={error}
        autoFocus
        value={text}
        placeholder="YYYY-MM-DD"
        onChange={(e) => {
          setText(e.target.value);
          setError(false);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
          if (e.key === "Escape") {
            cancelled.current = true;
            setEditing(false);
          }
        }}
        onBlur={() => {
          const d = !cancelled.current && parseDay(text);
          if (d) onChange(clampDate(d, min, max));
          setEditing(false);
        }}
      />
    </span>
  );
}

export default function Timeline({ startDate, endDate, value, onChange }) {
  const stops = useMemo(() => snapStops(startDate, endDate), [startDate, endDate]);
  const span = endDate - startDate;
  const pct = span > 0 ? ((value - startDate) / span) * 100 : 0;
  let index = 0;
  stops.forEach((s, i) => {
    if (Math.abs(s - value) < Math.abs(stops[index] - value)) index = i;
  });

  return (
    <div className="timeline-wrap">
      <div className="timeline-header">
        <span className="timeline-label">Memory Time Machine</span>
        <DateField value={value} min={startDate} max={endDate} onChange={onChange} />
      </div>

      <div className="timeline-track-wrap">
        <span className="timeline-bound">{fmtDate(startDate)}</span>
        <div className="timeline-track">
          <div className="timeline-fill" style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
          <div className="timeline-thumb" style={{ left: `${Math.min(100, Math.max(0, pct))}%` }} />
          <input
            type="range"
            min={0}
            max={stops.length - 1}
            step={1}
            value={index}
            onChange={(e) => onChange(stops[Number(e.target.value)])}
            className="timeline-slider"
            aria-label="Select date in memory"
            aria-valuetext={fmtDate(value)}
          />
        </div>
        <span className="timeline-bound">{fmtDate(endDate)}</span>
      </div>
    </div>
  );
}
