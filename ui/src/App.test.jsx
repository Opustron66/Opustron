import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import App from "./App";

const fact = (id, subject, object, from, to = null) => ({ fact_id: id, kind: 'claim', subject, predicate: 'owns', object, valid_from: from, valid_to: to, doc_id: `doc_${id}`, quote: `${subject} owns ${object}.` });
function serve(routes) {
  const spy = vi.fn(async (url) => {
    const path = url.split('?')[0];
    if (!(path in routes)) throw new Error(`down: ${path}`);
    return { ok: true, json: async () => routes[path] };
  });
  vi.stubGlobal('fetch', spy);
  return spy;
}
const live = {
  '/api/facts': [fact('a', 'Dana Lee', 'billing', '2026-06-01', '2026-06-20'), fact('b', 'Sam Ortiz', 'billing', '2026-06-20')],
  '/api/entities': [{ entity_id: 'billing', name: 'billing', entity_type: 'unknown' }],
  '/api/span': { start: '2026-06-01', end: '2026-06-30' },
  '/api/config': { chat_enabled: false, document_count: 425 },
};

test('a failed backend request shows a connection error instead of four sample facts', async () => {
  serve({});
  render(<App />);
  expect(await screen.findByText('Memory unavailable')).toBeInTheDocument();
  expect(screen.getByText('Saved memory is temporarily unavailable.')).toBeInTheDocument();
  expect(screen.queryByLabelText('Memory browser')).not.toBeInTheDocument();
  expect(screen.queryByText('Alice Chen')).not.toBeInTheDocument();
  expect(screen.queryByText('Browse-only demo')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Retry connection' })).toBeEnabled();
});

test('a delayed backend never renders sample facts while loading', async () => {
  serve({});
  vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
  const { unmount } = render(<App />);
  expect(screen.getByText('Connecting to saved memory…')).toBeInTheDocument();
  expect(screen.queryByLabelText('Memory browser')).not.toBeInTheDocument();
  unmount();
});

test('retry restores the real corpus and its actual chat configuration', async () => {
  serve({});
  render(<App />);
  await screen.findByText('Memory unavailable');
  serve({ ...live, '/api/config': { chat_enabled: true, document_count: 425 } });
  await userEvent.click(screen.getByRole('button', { name: 'Retry connection' }));
  await screen.findByText('Live memory');
  expect(screen.getByText('425')).toBeInTheDocument();
  expect(screen.getByLabelText('Ask a question')).toBeEnabled();
  expect(screen.getByText('Live chat · uses paid model calls')).toBeInTheDocument();
});

test('temporary configuration failure does not falsely report chat as disabled', async () => {
  const spy = serve({ ...live, '/api/config': undefined });
  spy.mockImplementation(async (url) => {
    const path = url.split('?')[0];
    if (path === '/api/config') throw new Error('502');
    return { ok: true, json: async () => live[path] || [] };
  });
  render(<App />);
  await screen.findByText('Memory unavailable');
  expect(screen.queryByText('Browse-only demo')).not.toBeInTheDocument();
  expect(screen.queryByText('Live memory')).not.toBeInTheDocument();
});

test('a transient request failure reconnects automatically', async () => {
  vi.useFakeTimers();
  try {
    serve({});
    render(<App />);
    await act(async () => {});
    expect(screen.getByText('Memory unavailable')).toBeInTheDocument();
    serve(live);
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(screen.getByText('Live memory')).toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
});

test('automatic retries stop after four attempts and never call chat', async () => {
  vi.useFakeTimers();
  try {
    const spy = serve({});
    render(<App />);
    await act(async () => { await vi.advanceTimersByTimeAsync(60000); });
    expect(spy.mock.calls.filter(([url]) => url === '/api/facts')).toHaveLength(4);
    expect(spy.mock.calls.some(([url]) => url === '/api/ask')).toBe(false);
    expect(screen.getByText('Memory unavailable')).toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
});

test('a successful empty response is distinct from a connection failure', async () => {
  serve({ '/api/facts': [], '/api/entities': [], '/api/span': { start: null, end: null }, '/api/config': { chat_enabled: false } });
  render(<App />);
  await screen.findByText('Waiting for memory');
  expect(screen.queryByText('Memory unavailable')).not.toBeInTheDocument();
});

test('live memory uses real facts and explains that paid chat is paused', async () => {
  const spy = serve({ ...live, '/api/facts': [...live['/api/facts'], { kind: 'note', content: 'Not an entity fact' }] });
  render(<App />);
  expect(await screen.findByText('Live memory')).toBeInTheDocument();
  expect(screen.getByText('425')).toBeInTheDocument();
  const detail = within(screen.getByLabelText('Selected memory'));
  expect(detail.getByText('Dana Lee').closest('.fact-row')).toHaveClass('fact-superseded');
  expect(detail.getByText('Sam Ortiz').closest('.fact-row')).toHaveClass('fact-current');
  expect(screen.getByText('Browse-only demo')).toBeInTheDocument();
  expect(screen.getByText('Browse-only demo · chat disabled')).toBeInTheDocument();
  expect(screen.getByLabelText('Chat unavailable in browse-only demo')).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: /Who owns what/ }));
  expect(screen.getByLabelText('Filter memory')).toHaveValue('owns');
  expect(spy.mock.calls.some(([url]) => url === '/api/ask')).toBe(false);
});

test('search selects matching people and reports no matches', async () => {
  serve(live);
  render(<App />);
  await screen.findByText('Live memory');
  await userEvent.type(screen.getByLabelText('Search entities'), 'Sam');
  expect(screen.getByRole('heading', { name: 'Sam Ortiz', level: 3 })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /Dana Lee/ })).not.toBeInTheDocument();
  await userEvent.type(screen.getByLabelText('Search entities'), 'zzzz');
  expect(screen.getByText(/No matches/)).toBeInTheDocument();
});

test('literal claim values are not presented as people or projects', async () => {
  serve({ ...live, '/api/facts': [...live['/api/facts'], { ...fact('c', 'Launch', 'scheduled', '2026-06-01'), predicate: 'status' }] });
  render(<App />);
  await screen.findByText('Live memory');
  const browser = within(screen.getByLabelText('Memory browser'));
  expect(browser.getByRole('button', { name: /Launch/ })).toBeInTheDocument();
  expect(browser.queryByRole('button', { name: /scheduled/ })).not.toBeInTheDocument();
  expect(browser.getByRole('button', { name: /billing/ })).toBeInTheDocument();
});

test('empty saved memory has a visitor-friendly message and no slider', async () => {
  serve({ '/api/facts': [], '/api/entities': [], '/api/span': { start: null, end: null }, '/api/config': { chat_enabled: false } });
  render(<App />);
  expect(await screen.findByText('Waiting for memory')).toBeInTheDocument();
  expect(screen.getByText('Your memory starts here.')).toBeInTheDocument();
  expect(screen.queryByLabelText('Select date in memory')).not.toBeInTheDocument();
});

test('source dates bound the timeline even when extracted claims reach 2110', async () => {
  serve({ ...live, '/api/span': { start: '2027-07-20', end: '2110-07-08' }, '/api/config': { chat_enabled: false, corpus_start: '2027-07-20', corpus_end: '2027-09-24', document_count: 173 } });
  const { container } = render(<App />);
  await screen.findByText('Live memory');
  expect(container.querySelector('.timeline-date')).toHaveTextContent('24 Sept 2027');
  expect(screen.queryByText(/2110/)).not.toBeInTheDocument();
});

test('comparison is a separate view rather than squeezing the memory panels', async () => {
  serve(live);
  render(<App />);
  await screen.findByText('Live memory');
  await userEvent.click(screen.getByRole('tab', { name: 'Compare dates' }));
  expect(screen.getByRole('heading', { name: 'See what changed.' })).toBeInTheDocument();
  expect(screen.queryByLabelText('Memory browser')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('tab', { name: 'Memory explorer' }));
  expect(screen.getByLabelText('Memory browser')).toBeInTheDocument();
});
