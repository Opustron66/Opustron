import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";
import DateDiff from "./DateDiff";
import { MOCK, diffFacts } from "../services/api";

const props = { startDate: MOCK.corpusStart, endDate: MOCK.corpusEnd, facts: MOCK.facts };

test("diffFacts pairs a handover as a change, not an add and an end", () => {
  const { added, ended, changed } = diffFacts(MOCK.facts, "2026-05-01", "2026-05-20");
  expect(changed.map((c) => [c.before.subject, c.after.subject])).toEqual([["Alice Chen", "Bob Nakamura"]]);
  expect(added).toEqual([]);
  expect(ended.map((f) => f.fact_id)).toEqual(["f4"]); // Bob's on-call ended 6 May
});

test("shows what changed and ended between the two dates", async () => {
  render(<DateDiff {...props} asOf={new Date("2026-05-01")} />);
  await userEvent.click(screen.getByText("Compare two dates"));

  expect(screen.getByRole("heading", { name: /Changed/ })).toBeVisible();
  expect(screen.getByText("Alice Chen")).toHaveClass("fact-change-before");
  expect(screen.getByText("Bob Nakamura")).toHaveClass("fact-change-after");
  expect(screen.getByText("Bob Nakamura · on call for: deploy pipeline")).toBeVisible();
  expect(screen.queryByRole("heading", { name: /Added/ })).not.toBeInTheDocument();
  // Alice leads the deploy pipeline on both dates: not a difference.
  expect(screen.queryByText(/leads: deploy pipeline/)).not.toBeInTheDocument();
});

test("says so when nothing changed", async () => {
  render(<DateDiff {...props} asOf={new Date("2026-05-20")} />);
  await userEvent.click(screen.getByText("Compare two dates"));
  fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-05-21" } });
  expect(screen.getByText("Nothing changed between these dates.")).toBeVisible();
});
