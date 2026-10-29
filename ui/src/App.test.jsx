import { fireEvent, render, screen, within } from "@testing-library/react";
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

test('offline preview is labelled and the selected entity follows the date', async () => {
  serve({});
  const { container } = render(<App />);
  expect(await screen.findByText('Preview data')).toBeInTheDocument();
  expect(screen.getByText(/four example facts/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /payments service/ }));
  const detail = within(screen.getByLabelText('Selected memory'));
  expect(detail.getByText('Alice Chen').closest('.fact-row')).toHaveClass('fact-current');
  fireEvent.change(screen.getByLabelText('Select date in memory'), { target: { value: '34' } });
  expect(container.querySelector('.timeline-date')).toHaveTextContent('20 May 2026');
  expect(detail.getByText('Alice Chen').closest('.fact-row')).toHaveClass('fact-superseded');
  expect(detail.getByText('Bob Nakamura').closest('.fact-row')).toHaveClass('fact-current');
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
  serve({ '/api/facts': [], '/api/entities': [], '/api/span': { start: null, end: null } });
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
