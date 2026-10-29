const BASE = "/api";

async function get(path, options) {
  const res = await (options ? fetch(`${BASE}${path}`, options) : fetch(`${BASE}${path}`));
  if (!res.ok) throw Object.assign(new Error(`${res.status} ${path}`), { status: res.status });
  return res.json();
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw Object.assign(new Error(`${res.status} ${path}`), { status: res.status });
  return res.json();
}

// P2 memory store (python -m chronicle.memory serve --state DIR)
export const getEntities = (options) => get("/entities", options);
export const getEntityHistory = (id) => get(`/entities/${id}/history`);
export const getFacts = (options) => get("/facts", options); // every fact, superseded included
export const getFactsAsOf = (isoDate) => get(`/facts?as_of=${isoDate}`);
export const getSpan = (options) => get("/span", options);
export const getConfig = (options) => get("/config", options);
export const getTimeline = (start, end) =>
  get(`/timeline?start=${start}&end=${end}`);

// P3 reasoning endpoint
export const ask = (question, asOf = null) =>
  post("/ask", { question, as_of: asOf });

// P4 egress log endpoint
export const getEgressLog = (n = 30) => get(`/egress?n=${n}`);

// ---------------------------------------------------------------------------
// Mock data — used when the backend is not running (scaffold phase)
// ---------------------------------------------------------------------------

const CORPUS_START = new Date("2026-04-16");
const CORPUS_END = new Date("2026-05-27");

export const MOCK = {
  corpusStart: CORPUS_START,
  corpusEnd: CORPUS_END,

  entities: [
    { entity_id: "e1", name: "payments service", entity_type: "unknown" },
    { entity_id: "e2", name: "deploy pipeline", entity_type: "unknown" },
    { entity_id: "e3", name: "Alice Chen", entity_type: "person" },
    { entity_id: "e4", name: "Bob Nakamura", entity_type: "person" },
  ],

  // Same shape and conventions as the memory store: (person, predicate, thing),
  // and valid_to is the first day the fact is no longer true.
  facts: [
    {
      fact_id: "f1",
      kind: "claim",
      subject: "Alice Chen",
      predicate: "owns",
      object: "payments service",
      valid_from: "2026-05-01",
      valid_to: "2026-05-15",
      doc_id: "email_001",
      quote: "Alice owns the payments service going forward.",
    },
    {
      fact_id: "f2",
      kind: "claim",
      subject: "Bob Nakamura",
      predicate: "owns",
      object: "payments service",
      valid_from: "2026-05-15",
      valid_to: null,
      doc_id: "email_042",
      quote: "Bob now owns the payments service.",
    },
    {
      fact_id: "f3",
      kind: "claim",
      subject: "Alice Chen",
      predicate: "leads",
      object: "deploy pipeline",
      valid_from: "2026-04-16",
      valid_to: null,
      doc_id: "email_003",
      quote: "Alice Chen is leading the deploy pipeline effort.",
    },
    {
      fact_id: "f4",
      kind: "claim",
      subject: "Bob Nakamura",
      predicate: "on_call_for",
      object: "deploy pipeline",
      valid_from: "2026-04-22",
      valid_to: "2026-05-06",
      doc_id: "chat_007",
      quote: "Bob is on-call for deploys this sprint.",
    },
  ],

  egressEntries: [
    {
      ts: new Date(Date.now() - 8000).toISOString(),
      provider: "nebius_token_factory",
      model: "nvidia/nemotron-mini-4b-instruct",
      prompt_tokens: 312,
      completion_tokens: 48,
      redacted: true,
      pii_types: ["PERSON"],
      request_preview: "Who owned ORG_1_service on 3 May?",
    },
    {
      ts: new Date(Date.now() - 22000).toISOString(),
      provider: "nebius_token_factory",
      model: "nvidia/nemotron-mini-4b-instruct",
      prompt_tokens: 204,
      completion_tokens: 31,
      redacted: false,
      pii_types: [],
      request_preview: "What is the current lead for the deploy pipeline?",
    },
  ],
};

// Half-open, like the memory store: true from valid_from (inclusive) until
// valid_to (exclusive). A missing valid_from means "since before we know".
export function isTrueAt(fact, when) {
  const d = new Date(when);
  const startedBy = !fact.valid_from || new Date(fact.valid_from) <= d;
  const notYetEnded = !fact.valid_to || d < new Date(fact.valid_to);
  return startedBy && notYetEnded;
}

export function hasEndedBy(fact, when) {
  return Boolean(fact.valid_to) && new Date(when) >= new Date(fact.valid_to);
}

export function factsAsOf(facts, when) {
  return facts.filter((f) => isTrueAt(f, when));
}

// Facts an entity appears in, on either side ("Alice owns payments" is about both).
export function factsAbout(facts, name) {
  return facts.filter((f) => f.subject === name || f.object === name);
}

// Two facts fill the same slot when they share the predicate and exactly one side:
// "Alice owns payments" -> "Bob owns payments", or "deadline: 1 May" -> "deadline: 8 May".
export function sameSlot(a, b) {
  return a.predicate === b.predicate && (a.subject === b.subject) !== (a.object === b.object);
}

const day = (iso) => (iso ? iso.slice(0, 10) : null);

// For the facts a cited document states, the fact each one replaced (the latest that ended by
// the time it started), as { before, after }.
export function replacedFacts(facts, docIds) {
  const cited = new Set(docIds);
  const seen = new Set();
  const out = [];
  facts
    .filter((f) => cited.has(f.doc_id) && f.valid_from)
    .forEach((after) => {
      const before = facts
        .filter((p) => p !== after && sameSlot(p, after) && p.valid_to && day(p.valid_to) <= day(after.valid_from))
        .sort((a, b) => (day(a.valid_to) < day(b.valid_to) ? 1 : -1))[0];
      if (before && !seen.has(before.fact_id)) {
        seen.add(before.fact_id);
        out.push({ before, after });
      }
    });
  return out;
}

// What changed in memory between two dates: facts that became true, stopped being true, and
// pairs where one replaced the other in the same slot.
export function diffFacts(facts, from, to) {
  const was = factsAsOf(facts, from);
  const now = factsAsOf(facts, to);
  let added = now.filter((f) => !was.includes(f));
  let ended = was.filter((f) => !now.includes(f));
  const changed = [];
  ended.forEach((before) => {
    const after = added.find((a) => sameSlot(before, a));
    if (after) {
      changed.push({ before, after });
      added = added.filter((a) => a !== after);
    }
  });
  ended = ended.filter((f) => !changed.some((c) => c.before === f));
  return { added, ended, changed };
}
