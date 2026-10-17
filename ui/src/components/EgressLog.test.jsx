import { render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import EgressLog from "./EgressLog";

test("shows mock entries labelled as sample data when the egress server is down", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
  render(<EgressLog />);
  expect(await screen.findByText("Who owned ORG_1_service on 3 May?")).toBeInTheDocument();
  expect(screen.getByText("🔒 redacted")).toBeInTheDocument();
  expect(screen.getByText("✓ clean")).toBeInTheDocument();
  expect(screen.getByText("sample data")).toBeInTheDocument();
  expect(screen.queryByText("● LIVE")).not.toBeInTheDocument();
});

test("replaces mock entries with the live log and says so", async () => {
  const entries = [
    {
      ts: "2026-10-17T12:00:00Z",
      model: "nvidia/nemotron-mini-4b-instruct",
      prompt_tokens: 10,
      completion_tokens: 3,
      redacted: true,
      request_preview: "When did PERSON_1 join?",
      // pii_types and provider omitted on purpose: the UI must tolerate partial records.
    },
  ];
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => entries }));
  render(<EgressLog />);

  expect(await screen.findByText("When did PERSON_1 join?")).toBeInTheDocument();
  expect(screen.queryByText("Who owned ORG_1_service on 3 May?")).not.toBeInTheDocument();
  expect(screen.getByText("● LIVE")).toBeInTheDocument();
  expect(screen.getByText("nemotron-mini-4b-instruct")).toBeInTheDocument();
  expect(screen.getByText("10↑ 3↓")).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith("/api/egress?n=30");
});

test("labels web searches and hides their zero token counts", async () => {
  const entries = [
    {
      ts: "2026-10-17T12:00:00Z",
      provider: "tavily",
      model: "search",
      prompt_tokens: 0,
      completion_tokens: 0,
      redacted: false,
      pii_types: [],
      request_preview: "NVIDIA OpenShell sandbox",
    },
  ];
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => entries }));
  render(<EgressLog />);

  expect(await screen.findByText("Tavily search")).toBeInTheDocument();
  expect(screen.queryByText("0↑ 0↓")).not.toBeInTheDocument();
});

test("shows an empty state when the live log has no calls", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
  render(<EgressLog />);
  expect(await screen.findByText("Nothing has left this machine yet.")).toBeInTheDocument();
});

test("says offline, not sample, when the server goes away after being live", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const real = [{ ts: "2026-10-17T12:00:00Z", provider: "tavily", redacted: false, request_preview: "real search" }];
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => real })
    .mockRejectedValue(new Error("down"));
  vi.stubGlobal("fetch", fetchMock);
  render(<EgressLog />);

  expect(await screen.findByText("● LIVE")).toBeInTheDocument();
  await vi.advanceTimersByTimeAsync(2100);
  await waitFor(() => expect(screen.getByText("offline")).toBeInTheDocument());
  expect(screen.getByText("real search")).toBeInTheDocument();
  expect(screen.queryByText("sample data")).not.toBeInTheDocument();
  vi.useRealTimers();
});
