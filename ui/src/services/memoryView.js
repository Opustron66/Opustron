import { factsAsOf } from "./api";

export const isoDay = (date) => new Date(date).toISOString().slice(0, 10);
export const formatDay = (date) => new Date(date).toLocaleDateString("en-GB", {
  day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
});

const objectSlots = new Set(["owns", "leads", "manages", "maintains"]);
const subjectSlots = new Set(["status", "deadline", "scheduled_for", "located_in", "reports_to", "works_at", "role", "owner", "owned_by", "lead", "led_by", "assigned_to", "on_call", "manager", "managed_by", "title"]);
const slot = (f) => objectSlots.has(f.predicate) ? `${f.predicate}|${f.object}`
  : subjectSlots.has(f.predicate) ? `${f.subject}|${f.predicate}` : null;

export function compareFacts(facts, from, to) {
  const before = factsAsOf(facts, from);
  const after = factsAsOf(facts, to);
  const oldIds = new Set(before.map((f) => f.fact_id));
  const newIds = new Set(after.map((f) => f.fact_id));
  let added = after.filter((f) => !oldIds.has(f.fact_id));
  let ended = before.filter((f) => !newIds.has(f.fact_id));
  const changed = [];
  ended.forEach((old) => {
    const replacement = slot(old) && added.find((f) => slot(f) === slot(old));
    if (replacement) {
      changed.push({ before: old, after: replacement });
      added = added.filter((f) => f !== replacement);
    }
  });
  const paired = new Set(changed.map((pair) => pair.before.fact_id));
  ended = ended.filter((f) => !paired.has(f.fact_id));
  return { changed, added, ended };
}

export function factSentence(fact) {
  const words = fact.predicate.replace(/^attr:/, "").replaceAll("_", " ");
  return `${fact.subject} · ${words} · ${fact.object}`;
}
