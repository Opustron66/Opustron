import React from "react";

const fmt = (iso) =>
  new Date(`${iso.slice(0, 10)}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  });

// "payments service · owns: Alice Chen → Bob Nakamura (15 May 26)"
export default function FactChange({ before, after }) {
  const shared = before.subject === after.subject ? "subject" : "object";
  const moved = shared === "subject" ? "object" : "subject";
  return (
    <span className="fact-change">
      <span className="fact-change-slot">
        {after[shared]} · {after.predicate.replace(/_/g, " ")}:
      </span>{" "}
      <span className="fact-change-before">{before[moved]}</span> →{" "}
      <span className="fact-change-after">{after[moved]}</span>
      {after.valid_from && <span className="fact-change-date"> ({fmt(after.valid_from)})</span>}
    </span>
  );
}
