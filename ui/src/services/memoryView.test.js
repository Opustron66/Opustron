import { expect, test } from 'vitest';
import { compareFacts } from './memoryView';

test('an ownership handover is one change and memberships are independent facts', () => {
  const old = { fact_id: 'a', subject: 'Alice', predicate: 'owns', object: 'payments', valid_from: '2026-05-01', valid_to: '2026-05-15' };
  const next = { ...old, fact_id: 'b', subject: 'Bob', valid_from: '2026-05-15', valid_to: null };
  const member = { ...old, fact_id: 'c', subject: 'Alice', predicate: 'member_of', object: 'team A' };
  const member2 = { ...member, fact_id: 'd', object: 'team B', valid_from: '2026-05-15', valid_to: null };
  const result = compareFacts([old, next, member, member2], '2026-05-10', '2026-05-20');
  expect(result.changed).toEqual([{ before: old, after: next }]);
  expect(result.added).toEqual([member2]);
  expect(result.ended).toEqual([member]);
});
