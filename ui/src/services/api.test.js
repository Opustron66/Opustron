import { describe, expect, test } from "vitest";
import { MOCK, factsAbout, factsAsOf, hasEndedBy, isTrueAt } from "./api";

const ids = (facts) => facts.map((f) => f.fact_id).sort();
const alice = MOCK.facts.find((f) => f.fact_id === "f1"); // owns payments 1 May → 15 May

describe("half-open validity, matching the memory store", () => {
  test("true from valid_from up to, not including, valid_to", () => {
    expect(isTrueAt(alice, "2026-04-30")).toBe(false);
    expect(isTrueAt(alice, "2026-05-01")).toBe(true);
    expect(isTrueAt(alice, "2026-05-14")).toBe(true);
    expect(isTrueAt(alice, "2026-05-15")).toBe(false);
  });

  test("has ended from valid_to onwards", () => {
    expect(hasEndedBy(alice, "2026-05-14")).toBe(false);
    expect(hasEndedBy(alice, "2026-05-15")).toBe(true);
  });

  test("a missing valid_from means true since before the corpus", () => {
    expect(isTrueAt({ valid_from: null, valid_to: "2026-05-01" }, "2020-01-01")).toBe(true);
  });

  test("works with full ISO datetimes from the store", () => {
    const note = { valid_from: "2026-05-01T09:30:00+00:00", valid_to: null };
    expect(isTrueAt(note, "2026-05-01T09:00:00Z")).toBe(false);
    expect(isTrueAt(note, "2026-05-01T10:00:00Z")).toBe(true);
  });
});

describe("factsAsOf", () => {
  test("exactly one owner of payments on the handover day", () => {
    const owners = (d) =>
      factsAsOf(MOCK.facts, d)
        .filter((f) => f.object === "payments service")
        .map((f) => f.subject);
    expect(owners("2026-05-14")).toEqual(["Alice Chen"]);
    expect(owners("2026-05-15")).toEqual(["Bob Nakamura"]);
  });

  test("treats a null valid_to as still true", () => {
    expect(ids(factsAsOf(MOCK.facts, "2026-12-31"))).toEqual(["f2", "f3"]);
  });

  test("returns nothing before the corpus starts", () => {
    expect(factsAsOf(MOCK.facts, "2026-04-15")).toEqual([]);
  });
});

test("factsAbout finds an entity on either side and keeps superseded facts", () => {
  expect(ids(factsAbout(MOCK.facts, "payments service"))).toEqual(["f1", "f2"]);
  expect(ids(factsAbout(MOCK.facts, "Alice Chen"))).toEqual(["f1", "f3"]);
});
