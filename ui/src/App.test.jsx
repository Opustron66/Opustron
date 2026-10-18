import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import App from "./App";

const card = (name) =>
  screen.getAllByRole("heading", { level: 3 }).find((h) => h.textContent === name).closest(".entity-card");
const rowIn = (cardName, value) => within(card(cardName)).getByText(value).closest(".fact-row");

const fact = (id, subject, predicate, object, valid_from, valid_to = null) => ({
  fact_id: id, kind: "claim", subject, predicate, object, valid_from, valid_to,
  doc_id: `doc_${id}`, quote: `${subject} ${predicate} ${object}.`, sources: [],
});

function serve(routes) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      const path = url.split("?")[0];
      if (!(path in routes)) throw new Error(`down: ${path}`);
      return { ok: true, json: async () => routes[path] };
    })
  );
}

test("without a memory server it shows sample data, and the slider changes who owns payments", async () => {
  serve({});
  const { container } = render(<App />);
  expect(await screen.findByText("Sample data · memory server not running")).toBeInTheDocument();
  expect(rowIn("payments service", "Alice Chen")).toHaveClass("fact-current");

  fireEvent.change(screen.getByLabelText("Select date in memory"), { target: { value: "34" } }); // 20 May
  expect(container.querySelector(".timeline-date")).toHaveTextContent("20 May 26");
  expect(screen.getByText("as of 20 May 26")).toBeInTheDocument();
  expect(rowIn("payments service", "Alice Chen")).toHaveClass("fact-superseded");
  expect(rowIn("payments service", "Bob Nakamura")).toHaveClass("fact-current");
});

test("with the memory server it shows real facts, skips notes, and starts at the latest day", async () => {
  serve({
    "/api/facts": [
      fact("a", "Dana Lee", "owns", "billing", "2026-06-01", "2026-06-20"),
      fact("b", "Sam Ortiz", "owns", "billing", "2026-06-20"),
      { fact_id: "n", kind: "note", subject: "", predicate: "", object: "", content: "User prefers tea",
        valid_from: "2026-06-05T10:00:00+00:00", valid_to: null, doc_id: "hermes://builtin/memory" },
    ],
    "/api/entities": [{ entity_id: "billing", name: "billing", entity_type: "unknown", fact_count: 2 }],
    "/api/span": { start: "2026-06-01", end: "2026-06-30" },
  });
  const { container } = render(<App />);

  expect(await screen.findByText("● Live memory · 2 facts")).toBeInTheDocument();
  expect(container.querySelector(".timeline-date")).toHaveTextContent("30 Jun 26");
  expect(rowIn("billing", "Dana Lee")).toHaveClass("fact-superseded");
  expect(rowIn("billing", "Sam Ortiz")).toHaveClass("fact-current");
  expect(screen.queryByText("payments service")).not.toBeInTheDocument();
  expect(screen.queryByText("User prefers tea")).not.toBeInTheDocument();
});

test("a running but empty memory server says how to fill it", async () => {
  serve({ "/api/facts": [], "/api/entities": [], "/api/span": { start: null, end: null } });
  render(<App />);
  expect(await screen.findByText("● Live memory · no facts yet")).toBeInTheDocument();
  expect(screen.getByText(/has no facts yet/)).toBeInTheDocument();
  expect(screen.queryByLabelText("Select date in memory")).not.toBeInTheDocument();
});
