# Full-system development evaluation

Completed on 18 October 2026 (Asia/Singapore), against `main` at `359f813c28debfadb2b6c7f00ab56005e704cb47`, using `nvidia/Nemotron-3_5-Lightning`, temperature 0 and a 16384-token completion budget. Product source code was not modified.

| Measure | Result |
|---|---|
| Automated Python checks | 333 passed |
| Automated UI checks | 34 passed |
| Production UI build | Passed |
| Cold ingestion | 6/6 documents, 9 claims, 0 failures |
| Persistent memory | 8 facts; handover checks and real server restart passed |
| Strictly supported live answers | **12/13 (92.3%)** on this synthetic set |
| HTTP/benchmark comparisons | 13/13 matching answers, citations and prompt hashes |
| Independent uncached CLI subset | 3/3 matched HTTP answers and citations |
| Browser checks | 8/8 passed after correcting a test-harness date-format assertion |
| Reliability checks | 7/7 passed; 2/2 real server-restart checks passed |
| Mean HTTP cold / warm latency | 5.165s / 0.288s |
| Warm HTTP and CLI provider calls | 0 |
| Actual live provider calls | 21, including ingestion and independent comparisons |
| Provider-reported usage | 11,125 prompt + 41,693 completion = 52,818 tokens |
| Synthetic full names / email exposed in outbound prompts | 0 occurrences of the four identifiers tested |

This is a development evaluation, not an official benchmark. The 13 questions do not establish general accuracy. The known cache defect is still reproducible; one answer overstates demo completion status, and extraction/retrieval data-quality issues remain. Read the findings before interpreting the passing tests as release readiness.

## Reports

1. [Setup, environment and complete corpus snapshot](01-setup-and-corpus.md)
2. [Frozen questions, expected answers and sources](02-frozen-expectations.md)
3. [Python test output](03-python-tests.md)
4. [UI test output](04-ui-tests.md)
5. [Production build output](05-ui-build.md)
6. [Staged ingestion, repeats, caches and all extracted claims](06-ingestion.md)
7. [Memory checks, stored facts, provenance and date snapshots](07-memory.md)
8. [Every live answer and cold/warm/CLI request result](08-live-answers.md)
9. [Manual extraction review](09-extraction-review.md)
10. [Reproduced empty-response/token-budget cache defect](10-cache-regressions.md)
11. [Final browser checks](11-browser.md), with [the preserved first attempt](11-browser-first-attempt.md)
12. [Input validation, provider-failure handling, HTTP APIs and restart](12-reliability-and-api.md)
13. [Prompt parity, cold/warm timing and token usage](13-comparisons-and-performance.md)
14. [Privacy audit, redacted transport trace and run egress records](14-privacy-and-transport.md)
15. [Per-question answer and citation grading](15-answer-grading.md)
16. [Exact retrieved evidence](16-retrieved-evidence.md)
17. [Findings, limitations and reproduction instructions](17-findings-and-next-steps.md)

Generated raw artifacts, isolated state, caches, screenshots and disposable test scripts are under `.tmp/full-system-2026-10-18-1709/`. All 19 human-readable reports are Markdown files in this dedicated report folder. The credential scan passed. Historical global egress logs were preserved. Evaluation servers were stopped after testing; preserved state can be served using the reproduction instructions. At evaluation completion, reports were still local; the later reports-only PR does not change the tested product source.
