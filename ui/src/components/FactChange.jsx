import React from "react";
import { fmtDate } from "../services/dates";

// "payments service · owns: Alice Chen → Bob Nakamura (15 May 2026)"
export default function FactChange({ before, after }) {
  const shared = before.subject === after.subject ? "subject" : "object";
  const moved = shared === "subject" ? "object" : "subject";
  return (
    <span className="fact-change">
      <span className="fact-change-slot">
        {after[shared]} · {after.predicate.replace(/^attr:/, "").replace(/_/g, " ")}:
      </span>{" "}
      <span className="fact-change-before">{before[moved]}</span> →{" "}
      <span className="fact-change-after">{after[moved]}</span>
      {after.valid_from && <span className="fact-change-date"> ({fmtDate(after.valid_from)})</span>}
    </span>
  );
}
