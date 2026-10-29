import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
      {...props}
    />
  );

test("shows the selected day and the corpus bounds in UTC, with full years", () => {
  renderTimeline();
  expect(screen.getByRole("button", { name: /10 May 2026/ })).toBeInTheDocument();
  expect(screen.getByText("16 Apr 2026")).toBeInTheDocument();
  expect(screen.getByText("27 May 2026")).toBeInTheDocument();
});

test("the slider snaps to month and mid-month stops", () => {
  const onChange = vi.fn();
  renderTimeline({ onChange });
  const slider = screen.getByLabelText("Select date in memory");
  expect(slider).toHaveAttribute("max", "3"); // 16 Apr, 1 May, 15 May, 27 May
  fireEvent.change(slider, { target: { value: "1" } });
  expect(onChange).toHaveBeenCalledWith(new Date("2026-05-01"));
});

test("clicking the date lets you type an exact day", async () => {
  const onChange = vi.fn();
  renderTimeline({ onChange });
  await userEvent.click(screen.getByRole("button", { name: /10 May 2026/ }));
  const field = screen.getByLabelText("Type a date");
  await userEvent.clear(field);
  await userEvent.type(field, "12 May 2026{Enter}");
  expect(onChange).toHaveBeenCalledWith(new Date("2026-05-12"));
});

test("a typed day outside the corpus is clamped, and nonsense is rejected", async () => {
  const onChange = vi.fn();
  renderTimeline({ onChange });
  await userEvent.click(screen.getByRole("button", { name: /10 May 2026/ }));
  const field = screen.getByLabelText("Type a date");
  await userEvent.clear(field);
  await userEvent.type(field, "soon{Enter}");
  expect(field).toHaveAttribute("aria-invalid", "true");
  expect(onChange).not.toHaveBeenCalled();
  await userEvent.clear(field);
  await userEvent.type(field, "2030-01-01{Enter}");
  expect(onChange).toHaveBeenCalledWith(new Date("2026-05-27"));
});

test("Escape leaves the date unchanged", async () => {
  const onChange = vi.fn();
  renderTimeline({ onChange });
  await userEvent.click(screen.getByRole("button", { name: /10 May 2026/ }));
  await userEvent.type(screen.getByLabelText("Type a date"), "{Escape}");
  expect(onChange).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: /10 May 2026/ })).toBeInTheDocument();
});
