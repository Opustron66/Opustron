import { expect, test } from "vitest";
import { describeChange, describeStatusAt, describeValidity, humanizeFact } from "./humanize";
import { fmtDate, parseDay, snapStops } from "./dates";

const f = (subject, predicate, object, extra = {}) => ({ subject, predicate, object, ...extra });

test("known predicates read as sentences", () => {
  expect(humanizeFact(f("Alex Chen", "assigned_to", "post-mortem for ingest cost spike"))).toBe(
    "Alex Chen is assigned to post-mortem for ingest cost spike."
  );
  expect(humanizeFact(f("Bob Nakamura", "on_call_for", "deploy pipeline"))).toBe("Bob Nakamura is on call for deploy pipeline.");
  expect(humanizeFact(f("Rohan Dasgupta", "works_on", "Beacon"))).toBe("Rohan Dasgupta is working on Beacon.");
});

test("attributes read as a property of the subject", () => {
  expect(humanizeFact(f("pool-fast", "attr:cores", "8"))).toBe("pool-fast's cores is 8.");
  expect(humanizeFact(f("Atlas", "attr:user_visible_errors", "zero"))).toBe("Atlas' user visible errors is zero.");
});

test("placeholder objects that repeat the predicate are dropped", () => {
  expect(humanizeFact(f("Platform Sync", "scheduled_for", "scheduled"))).toBe("Platform Sync is on the schedule.");
  expect(humanizeFact(f("shared CI pool", "scheduled_for", "split into pool-fast and pool-heavy"))).toBe(
    "shared CI pool is scheduled for split into pool-fast and pool-heavy."
  );
});

test("unknown predicates fall back to their words, with 'is' before a participle", () => {
  expect(humanizeFact(f("Alice", "mentored", "Bob"))).toBe("Alice mentored Bob.");
  expect(humanizeFact(f("Alice", "reviews", "the RFC"))).toBe("Alice reviews the RFC.");
  expect(humanizeFact(f("wave", "approved_by", "Jordan"))).toBe("wave is approved by Jordan.");
});

test("validity and status describe the dates in full", () => {
  expect(describeValidity({ valid_from: "2026-05-01", valid_to: "2026-05-15" })).toBe("True from 1 May 2026 until 15 May 2026.");
  expect(describeValidity({ valid_from: "2026-05-15", valid_to: null })).toBe("True since 15 May 2026.");
  expect(describeValidity({ valid_from: null, valid_to: null })).toBe("No dates were recorded for this.");
  const fact = { valid_from: "2026-05-01", valid_to: "2026-05-15" };
  expect(describeStatusAt(fact, new Date("2026-05-15"))).toBe("By 15 May 2026 this was no longer true.");
});

test("a change reads as before and after", () => {
  const before = f("Alice Chen", "owns", "payments service");
  const after = f("Bob Nakamura", "owns", "payments service", { valid_from: "2026-05-15" });
  expect(describeChange(before, after)).toBe(
    "Until 15 May 2026: Alice Chen owns payments service. From then on: Bob Nakamura owns payments service."
  );
});

test("dates show four-digit years and parse both typed forms", () => {
  expect(fmtDate("2026-05-10")).toBe("10 May 2026");
  expect(parseDay("2026-05-12").toISOString()).toBe("2026-05-12T00:00:00.000Z");
  expect(parseDay("12 May 2026").toISOString()).toBe("2026-05-12T00:00:00.000Z");
  expect(parseDay("not a date")).toBeNull();
});

test("slider stops snap to months, or half-months for short spans", () => {
  const iso = (ds) => ds.map((d) => d.toISOString().slice(0, 10));
  expect(iso(snapStops(new Date("2026-04-16"), new Date("2026-05-27")))).toEqual([
    "2026-04-16", "2026-05-01", "2026-05-15", "2026-05-27",
  ]);
  const long = iso(snapStops(new Date("2026-01-01"), new Date("2026-10-28")));
  expect(long[0]).toBe("2026-01-01");
  expect(long[1]).toBe("2026-02-01");
  expect(long.at(-2)).toBe("2026-10-01");
  expect(long.at(-1)).toBe("2026-10-28");
});
