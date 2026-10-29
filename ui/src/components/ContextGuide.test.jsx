import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterAll, beforeAll, expect, test, vi } from 'vitest';
import ContextGuide from './ContextGuide';

// jsdom has no native dialog methods. Real focus/Escape behavior is checked in Edge.
const originalShow = HTMLDialogElement.prototype.showModal;
const originalClose = HTMLDialogElement.prototype.close;
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
});
afterAll(() => {
  HTMLDialogElement.prototype.showModal = originalShow;
  HTMLDialogElement.prototype.close = originalClose;
});

test('the guide opens, explains the setting and provides all seven question types without network calls', async () => {
  const fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  render(<ContextGuide />);
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Demo guide' }));
  const guide = within(screen.getByRole('dialog', { name: 'Meet the story behind the memory.' }));
  expect(guide.getByText(/Imagine joining a fictional software team/)).toBeInTheDocument();
  expect(guide.getByText('Memory Time Machine to 27 May 2026')).toBeInTheDocument();
  expect(guide.getAllByRole('button', { name: /Copy question/ })).toHaveLength(7);
  expect(guide.getByText('Check honesty')).toBeInTheDocument();
  await userEvent.click(guide.getByRole('button', { name: 'Got it' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});

test('a question copies to the clipboard without submitting a paid chat request', async () => {
  const user = userEvent.setup();
  const copy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue();
  const fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  render(<ContextGuide />);
  await user.click(screen.getByRole('button', { name: 'Demo guide' }));
  await user.click(screen.getByRole('button', { name: 'Copy question 5' }));
  expect(copy).toHaveBeenCalledWith('As of 15 May 2026, had the senior backend engineer candidate accepted?');
  expect(screen.getByRole('status')).toHaveTextContent('Question 5 copied');
  expect(fetch).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Close demo guide' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

test('reference answers stay expandable and include the historical and unknown-project cases', async () => {
  render(<ContextGuide />);
  await userEvent.click(screen.getByRole('button', { name: 'Demo guide' }));
  const summaries = screen.getAllByText('Expected answer');
  expect(summaries).toHaveLength(7);
  const historical = summaries[4].closest('details');
  expect(historical).not.toHaveAttribute('open');
  await userEvent.click(summaries[4]);
  expect(historical).toHaveAttribute('open');
  expect(historical).toHaveTextContent('still at the offer stage');
  expect(summaries[6].closest('details')).toHaveTextContent('does not record that project');
});

test('clipboard failure keeps the question available for manual copying', async () => {
  const user = userEvent.setup();
  vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(new Error('not allowed'));
  render(<ContextGuide />);
  await user.click(screen.getByRole('button', { name: 'Demo guide' }));
  await user.click(screen.getByRole('button', { name: 'Copy question 1' }));
  expect(screen.getByRole('status')).toHaveTextContent('select and copy the question text');
  expect(screen.getByText('Who owns Beacon’s eval framework, and who owns the evaluator metric decision?')).toBeInTheDocument();
});
