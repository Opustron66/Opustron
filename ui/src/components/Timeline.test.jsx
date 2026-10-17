import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import Timeline from "./Timeline";
import { MOCK } from "../services/api";

const renderTimeline = (props = {}) =>
  render(
    <Timeline
      startDate={MOCK.corpusStart}
      endDate={MOCK.corpusEnd}
      value={new Date("2026-05-10")}
      onChange={() => {}}
      facts={MOCK.facts}
      {...props}
    />
  );

test("shows the selected day and the corpus bounds in UTC", () => {
  renderTimeline();
  expect(screen.getByText("10 May 26")).toBeInTheDocument();
  expect(screen.getByText("16 Apr 26")).toBeInTheDocument();
  expect(screen.getByText("27 May 26")).toBeInTheDocument();
});

test("moving the slider reports the matching date", () => {
  const onChange = vi.fn();
  renderTimeline({ onChange });
  fireEvent.change(screen.getByLabelText("Select date in memory"), { target: { value: "29" } });
  expect(onChange).toHaveBeenCalledWith(new Date("2026-05-15"));
});

const activeTitles = (container) =>
  [...container.querySelectorAll(".timeline-fact-bar.active")].map((el) => el.title);

test("highlights only the facts true on the selected day", () => {
  const { container } = renderTimeline({ value: new Date("2026-05-20") });
  const active = activeTitles(container);
  expect(active).toHaveLength(2);
  expect(active.join()).toContain("Bob Nakamura — owns: payments service");
  expect(active.join()).not.toContain("Alice Chen — owns");
});

test("on the handover day only the new owner's bar is active", () => {
  const { container } = renderTimeline({ value: new Date("2026-05-15") });
  const owners = activeTitles(container).filter((t) => t.includes("owns: payments service"));
  expect(owners).toEqual([expect.stringContaining("Bob Nakamura")]);
});
