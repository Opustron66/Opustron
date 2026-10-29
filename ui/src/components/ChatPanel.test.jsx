import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import ChatPanel from "./ChatPanel";

const asOf = new Date("2026-05-10");

const answerWith = (body) =>
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => body }));

const askQuestion = async (text) => {
  await userEvent.type(screen.getByRole("textbox"), `${text}{Enter}`);
};

test("header shows the as-of day in UTC", () => {
  render(<ChatPanel asOf={asOf} />);
  expect(screen.getByText("as of 10 May 2026")).toBeInTheDocument();
});

test("sends the question with the as-of date", async () => {
  answerWith({ answer: "Alice Chen.", citations: [{ doc_id: "email_001" }] });
  render(<ChatPanel asOf={asOf} />);
  await askQuestion("Who owned payments?");

  expect(await screen.findByText("Alice Chen.")).toBeInTheDocument();
  expect(screen.getByText("email_001")).toBeInTheDocument();
  const [url, init] = fetch.mock.calls[0];
  expect(url).toBe("/api/ask");
  expect(JSON.parse(init.body)).toEqual({ question: "Who owned payments?", as_of: "2026-05-10" });
});

test("shows an error without invented facts or citations when the backend is down", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connection refused")));
  render(<ChatPanel asOf={asOf} />);
  await askQuestion("Who owned payments?");
  expect(await screen.findByText(/Unable to get an answer/)).toBeInTheDocument();
  expect(screen.queryByText(/Alice Chen owned/)).not.toBeInTheDocument();
  expect(screen.queryByText("email_001")).not.toBeInTheDocument();
});

test("shows an error on a failed model response and permits another question", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 502 }));
  render(<ChatPanel asOf={asOf} />);
  await askQuestion("Who owned billing on June 9?");
  expect(await screen.findByText(/Unable to get an answer/)).toBeInTheDocument();
  expect(screen.queryByText("email_001")).not.toBeInTheDocument();
  expect(screen.getByRole("textbox")).toBeEnabled();
});

test("renders answer text as text, never as HTML", async () => {
  answerWith({ answer: '<img src=x onerror="window.pwned=1"> owner is **Bob**', citations: [] });
  const { container } = render(<ChatPanel asOf={asOf} />);
  await askQuestion("Who owns payments?");

  expect(await screen.findByText(/owner is/)).toHaveTextContent('<img src=x onerror="window.pwned=1"> owner is Bob');
  expect(container.querySelector("img")).toBeNull();
  expect(screen.getByText("Bob").tagName).toBe("STRONG");
  expect(window.pwned).toBeUndefined();
});

test("Enter on an empty box sends nothing", async () => {
  const fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);
  render(<ChatPanel asOf={asOf} />);
  await askQuestion("   ");
  expect(fetchSpy).not.toHaveBeenCalled();
});

const handover = [
  { fact_id: "f1", subject: "Alice Chen", predicate: "owns", object: "payments service",
    valid_from: "2026-05-01", valid_to: "2026-05-15", doc_id: "email_001" },
  { fact_id: "f2", subject: "Bob Nakamura", predicate: "owns", object: "payments service",
    valid_from: "2026-05-15", valid_to: null, doc_id: "email_042" },
];

test("Why? shows the quotes, the as-of date and the fact the answer replaced", async () => {
  answerWith({
    answer: "Bob Nakamura.",
    citations: [{ doc_id: "email_042" }],
    support: [{ doc_id: "email_042", quote: "Bob now owns the payments service." }],
    as_of: "2026-05-20",
    refused: false,
  });
  render(<ChatPanel asOf={asOf} facts={handover} />);
  await askQuestion("Who owns payments?");

  await userEvent.click(await screen.findByText("Why?"));
  expect(screen.getByText('"Bob now owns the payments service."')).toBeVisible();
  expect(screen.getByText("20 May 2026")).toBeVisible();
  expect(screen.getByText("Alice Chen")).toHaveClass("fact-change-before");
  expect(screen.getByText("Bob Nakamura")).toHaveClass("fact-change-after");
});

test("a refusal is a 'Not in memory' card with no Why? panel", async () => {
  answerWith({ answer: "Not in the corpus", citations: [], support: [], as_of: null, refused: true });
  render(<ChatPanel asOf={asOf} facts={handover} />);
  await askQuestion("What's on the cafeteria menu?");

  expect(await screen.findByText("Not in memory")).toBeInTheDocument();
  expect(screen.getByText("Not in the corpus").closest(".chat-message")).toHaveClass("chat-refusal");
  expect(screen.queryByText("Why?")).not.toBeInTheDocument();
});

test("an answer with nothing to explain has no Why? panel", async () => {
  answerWith({ answer: "Alice Chen.", citations: [] });
  render(<ChatPanel asOf={asOf} />);
  await askQuestion("Who owned payments?");
  expect(await screen.findByText("Alice Chen.")).toBeInTheDocument();
  expect(screen.queryByText("Why?")).not.toBeInTheDocument();
});

test("an empty chat suggests questions, and clicking one asks it", async () => {
  answerWith({ answer: "Bob Nakamura.", citations: [] });
  render(<ChatPanel asOf={asOf} />);
  await userEvent.click(screen.getByRole("button", { name: "Who owned payments in March?" }));
  expect(await screen.findByText("Bob Nakamura.")).toBeInTheDocument();
  expect(JSON.parse(fetch.mock.calls[0][1].body).question).toBe("Who owned payments in March?");
  expect(screen.queryByRole("button", { name: "Who owned payments in March?" })).not.toBeInTheDocument();
});

test("chats are saved by day and come back after a reload", async () => {
  answerWith({ answer: "Alice Chen.", citations: [] });
  const { unmount } = render(<ChatPanel asOf={asOf} />);
  await askQuestion("Who owned payments?");
  await screen.findByText("Alice Chen.");

  const stored = JSON.parse(localStorage.getItem("chronicle.chats"));
  const [day] = Object.keys(stored);
  expect(day).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  expect(stored[day][0].messages.map((m) => m.content)).toEqual(["Who owned payments?", "Alice Chen."]);

  unmount();
  render(<ChatPanel asOf={asOf} />);
  expect(screen.getByText("Alice Chen.")).toBeInTheDocument();
});

test("New chat starts empty, and History reopens the earlier one", async () => {
  answerWith({ answer: "Alice Chen.", citations: [] });
  render(<ChatPanel asOf={asOf} />);
  await askQuestion("Who owned payments?");
  await screen.findByText("Alice Chen.");

  await userEvent.click(screen.getByRole("button", { name: "New chat" }));
  expect(screen.queryByText("Alice Chen.")).not.toBeInTheDocument();
  expect(screen.getByText("What would you like to remember?")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: /History/ }));
  expect(screen.getByText("Today")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Who owned payments\?/ }));
  expect(screen.getByText("Alice Chen.")).toBeInTheDocument();
});

test("an unavailable demo budget explains that memory browsing still works", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));
  render(<ChatPanel asOf={asOf} />);
  await askQuestion("Who owns billing?");
  expect(await screen.findByText(/Live chat is unavailable or its demo budget has been used/)).toBeInTheDocument();
  expect(screen.getByText(/You can still explore saved facts and sources/)).toBeInTheDocument();
});
