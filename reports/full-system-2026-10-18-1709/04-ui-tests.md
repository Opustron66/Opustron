# ui-tests

Command: `npm.cmd test`

Exit code: 0. Duration: 10.98s.

```text

> chronicle-ui@0.1.0 test
> vitest run


 RUN  v2.1.9 C:/Github Projects/Opustron/ui

 ✓ src/services/api.test.js (8 tests) 16ms
 ✓ src/test/timezone.test.js (1 test) 71ms
 ✓ src/components/Timeline.test.jsx (4 tests) 310ms
 ✓ src/components/EgressLog.test.jsx (5 tests) 467ms
 ✓ src/components/EntityCard.test.jsx (7 tests) 729ms
   ✓ citation popover opens with the source quote and closes on outside click 420ms
 ✓ src/App.test.jsx (3 tests) 1192ms
   ✓ without a memory server it shows sample data, and the slider changes who owns payments 725ms
   ✓ with the memory server it shows real facts, skips notes, and starts at the latest day 307ms
 ✓ src/components/ChatPanel.test.jsx (6 tests) 2198ms
   ✓ sends the question with the as-of date 729ms
   ✓ shows an error without invented facts or citations when the backend is down 461ms
   ✓ shows an error on a failed model response and permits another question 394ms

 Test Files  7 passed (7)
      Tests  34 passed (34)
   Start at  17:12:39
   Duration  9.71s (transform 875ms, setup 9.16s, collect 2.92s, tests 4.98s, environment 33.60s, prepare 2.94s)


[33mThe CJS build of Vite's Node API is deprecated. See https://vite.dev/guide/troubleshooting.html#vite-cjs-node-api-deprecated for more details.[39m

```
