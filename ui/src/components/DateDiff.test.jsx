import { fireEvent, render, screen } from "@testing-library/react";
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

test("shows in plain English what changed and ended between the two dates", async () => {
  render(<DateDiff {...props} asOf={new Date("2026-05-27")} />);
  fireEvent.change(screen.getByLabelText("Compare from"), { target: { value: "2026-05-01" } });

  expect(screen.getByRole("heading", { name: /Changed/ })).toBeVisible();
  expect(screen.getByText("Alice Chen")).toHaveClass("fact-change-before");
  expect(screen.getByText("Bob Nakamura")).toHaveClass("fact-change-after");
  expect(screen.getByText(/Until 15 May 2026: Alice Chen owns payments service\. From then on: Bob Nakamura owns/)).toBeVisible();
  expect(screen.getByText("Bob Nakamura is on call for deploy pipeline.")).toBeVisible();
  expect(screen.getByText("No added facts")).toBeVisible();
  // Alice leads the deploy pipeline on both dates: not a difference.
  expect(screen.queryByText(/leads: deploy pipeline/)).not.toBeInTheDocument();
});

test("says so when nothing changed", async () => {
  render(<DateDiff {...props} asOf={new Date("2026-05-21")} />);
  fireEvent.change(screen.getByLabelText("Compare from"), { target: { value: "2026-05-20" } });
  expect(screen.getByText("Nothing changed between 20 May 2026 and 21 May 2026.")).toBeVisible();
});

test("opens on the month leading up to the selected day", () => {
  render(<DateDiff {...props} asOf={new Date("2026-05-20")} />);
  expect(screen.getByLabelText("Compare from")).toHaveValue("2026-04-20");
  expect(screen.getByLabelText("Compare to")).toHaveValue("2026-05-20");
});

test("rejects a reversed date range", () => {
  render(<DateDiff {...props} />);
  fireEvent.change(screen.getByLabelText("Compare from"), { target: { value: "2026-05-27" } });
  fireEvent.change(screen.getByLabelText("Compare to"), { target: { value: "2026-05-01" } });
  expect(screen.getByRole("alert")).toHaveTextContent("Choose an end date on or after the start date.");
});
