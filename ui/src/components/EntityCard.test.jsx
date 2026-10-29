import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";
import EntityCard from "./EntityCard";
import { MOCK } from "../services/api";

const entity = (name) => MOCK.entities.find((e) => e.name === name);
const row = (name) => screen.getByText(name).closest(".fact-row");

const renderCard = (name, asOf) =>
  render(<EntityCard entity={entity(name)} allFacts={MOCK.facts} asOf={new Date(asOf)} />);

test("the payments card lists who owns it, from the object side", () => {
  renderCard("payments service", "2026-05-10");
  expect(screen.getByText("who owns")).toBeInTheDocument();
  expect(row("Alice Chen")).toHaveClass("fact-current");
  expect(row("Bob Nakamura")).not.toHaveClass("fact-current");
  expect(row("Bob Nakamura")).not.toHaveClass("fact-superseded");
});

test("on the handover day only the new owner is current", () => {
  renderCard("payments service", "2026-05-15");
  expect(row("Alice Chen")).toHaveClass("fact-superseded");
  expect(row("Alice Chen")).not.toHaveClass("fact-current");
  expect(row("Bob Nakamura")).toHaveClass("fact-current");
});

test("a person's card reads from the subject side", () => {
  renderCard("Alice Chen", "2026-05-20");
  expect(screen.getByText("owns")).toBeInTheDocument();
  expect(screen.getByText("leads")).toBeInTheDocument();
  expect(row("payments service")).toHaveClass("fact-superseded");
  expect(row("deploy pipeline")).toHaveClass("fact-current");
});

test("predicates with underscores read as words", () => {
  renderCard("Bob Nakamura", "2026-05-01");
  expect(screen.getByText("on call for")).toBeInTheDocument();
});

test("validity dates display the stored day, not the day before", () => {
  renderCard("payments service", "2026-05-20");
  expect(screen.getByText("1 May 2026 → 15 May 2026")).toBeInTheDocument();
  expect(screen.getByText("15 May 2026 → now")).toBeInTheDocument();
});

test("an unknown start date says so", () => {
  const fact = { ...MOCK.facts[1], fact_id: "x", valid_from: null };
  render(<EntityCard entity={entity("payments service")} allFacts={[fact]} asOf={new Date("2026-05-20")} />);
  expect(screen.getByText("unknown → now")).toBeInTheDocument();
});

test("no raw source codes are shown on the card", () => {
  renderCard("payments service", "2026-05-10");
  expect(screen.queryByText(/email_0/)).not.toBeInTheDocument();
});

test("clicking a fact explains it in plain English", async () => {
  renderCard("payments service", "2026-05-20");
  const toggle = within(row("Alice Chen")).getByRole("button", { name: /Alice Chen/ });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  await userEvent.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByText("Alice Chen owns payments service.")).toBeInTheDocument();
  expect(screen.getByText(/True from 1 May 2026 until 15 May 2026\. By 20 May 2026 this was no longer true\./)).toBeInTheDocument();
  await userEvent.click(toggle);
  expect(screen.queryByText("Alice Chen owns payments service.")).not.toBeInTheDocument();
});
