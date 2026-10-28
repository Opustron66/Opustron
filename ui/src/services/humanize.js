import { fmtDate } from "./dates";
import { hasEndedBy, isTrueAt } from "./api";

const words = (predicate) => predicate.replace(/^attr:/, "").replaceAll("_", " ").trim();
const possessive = (name) => (/s$/i.test(name) ? `${name}'` : `${name}'s`);
const sentence = (text) => {
  const t = text.trim();
  return /[.!?]$/.test(t) ? t : `${t}.`;
};

// Objects the extractor fills with a placeholder that only repeats the predicate.
const EMPTY_OBJECT = { scheduled_for: ["scheduled"], deadline: ["due"] };

const TEMPLATES = {
  owns: (s, o) => `${s} owns ${o}`,
  leads: (s, o) => `${s} leads ${o}`,
  manages: (s, o) => `${s} manages ${o}`,
  on_call_for: (s, o) => `${s} is on call for ${o}`,
  reports_to: (s, o) => `${s} reports to ${o}`,
  works_on: (s, o) => `${s} is working on ${o}`,
  works_at: (s, o) => `${s} is part of ${o}`,
  member_of: (s, o) => `${s} is a member of ${o}`,
  assigned_to: (s, o) => `${s} is assigned to ${o}`,
  blocked_by: (s, o) => `${s} is blocked by ${o}`,
  located_in: (s, o) => `${s} takes place at ${o}`,
  role: (s, o) => `${s} acts as ${o}`,
  email: (s, o) => `${possessive(s)} email address is ${o}`,
  status: (s, o) => `${possessive(s)} status: ${o}`,
  decided: (s, o) => `The decision on ${s} was: ${o}`,
  proposed: (s, o) => `${s} proposed ${o}`,
  requested: (s, o) => `${s} asked for ${o}`,
  completed: (s, o) => `${s} finished ${o}`,
  scheduled_for: (s, o) => (o ? `${s} is scheduled for ${o}` : `${s} is on the schedule`),
  deadline: (s, o) => (o ? `${s} is due by ${o}` : `${s} has a deadline`),
};

// "pool-fast · attr:cores: 8" -> "pool-fast's cores is 8."
// "Alex Chen · assigned_to: post-mortem" -> "Alex Chen is assigned to post-mortem."
export function humanizeFact(fact) {
  const { subject: s, predicate: p } = fact;
  const o = EMPTY_OBJECT[p]?.includes(String(fact.object).toLowerCase()) ? "" : fact.object;
  if (TEMPLATES[p]) return sentence(TEMPLATES[p](s, o));
  if (p.startsWith("attr:")) return sentence(`${possessive(s)} ${words(p)} is ${o}`);
  const w = words(p);
  // Past participles read as a state: "blocked by" -> "is blocked by".
  const verb = /^\w+ed (by|to|for|in|on|with|from|at|of|as|into)\b/.test(w) ? `is ${w}` : w;
  return sentence(`${s} ${verb} ${o}`);
}

// valid_to is the first day a fact is no longer true.
export function describeValidity(fact) {
  const from = fact.valid_from && fmtDate(fact.valid_from);
  const to = fact.valid_to && fmtDate(fact.valid_to);
  if (from && to) return `True from ${from} until ${to}.`;
  if (from) return `True since ${from}.`;
  if (to) return `True until ${to}; when it started isn't recorded.`;
  return "No dates were recorded for this.";
}

export function describeStatusAt(fact, when) {
  const day = fmtDate(when);
  if (isTrueAt(fact, when)) return `On ${day} this was true.`;
  if (hasEndedBy(fact, when)) return `By ${day} this was no longer true.`;
  return `On ${day} this wasn't true yet.`;
}

// The two halves of a handover, as plain sentences.
export function describeChange(before, after) {
  const day = after.valid_from ? fmtDate(after.valid_from) : null;
  const was = humanizeFact(before);
  const now = humanizeFact(after);
  return day ? `Until ${day}: ${was} From then on: ${now}` : `Before: ${was} Later: ${now}`;
}
