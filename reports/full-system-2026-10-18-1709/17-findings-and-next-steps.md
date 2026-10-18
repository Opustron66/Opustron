# Findings and recommended next steps

No product-code fix was made during this evaluation. The only corrected code was the disposable browser test harness: its first attempt expected a zero-padded `09 Jun` label, while the UI correctly renders `9 Jun`. The first result is preserved in [the first browser report](11-browser-first-attempt.md); all eight checks pass after correcting that assertion in [the final browser report](11-browser.md).

## High: empty response caching prevents effective retries

Reproduced with an isolated synthetic transport. An empty response at 8192 tokens is cached. Retrying with 16384 reuses it because `max_tokens` is absent from the response-cache key. The live 16384-token cold run did not hit an empty response, but that does not fix the underlying defect.

Recommended fix: reject empty responses before caching; include effective generation settings in the key; invalidate or bypass invalid cached structured responses; preserve finish-reason diagnostics without exposing corpus text or credentials. See [the regression report](10-cache-regressions.md).

## Medium: unsupported certainty about completion

The document establishes that a demo is scheduled and explicitly does not report completion. The model answered: “No, the customer demo is scheduled for 2026-06-30 and has not been completed as of 2026-06-20.” This is stronger than the frozen expectation “completion not established; scheduled only.” The fallback answer contract itself says “Something only scheduled has not happened,” which encourages that inference. Tighten it to distinguish absence of evidence from evidence of absence and add a regression case. See [answer grading](15-answer-grading.md).

## Medium: extraction representation can create stray temporal facts

The model extracted a second deadline-closing claim with unknown start and an end at the old due date, June 18, even though the old deadline was replaced on June 12. Its object text also differs from the original claim. P2 correctly supersedes the primary deadline but retains this extra closing-only record. Email was also classified as `status`. Both values can still be answered correctly on this corpus, so answer accuracy alone would hide these data-quality issues. See [extraction review](09-extraction-review.md).

## Medium: question date tokens produce irrelevant retrieval matches

The before-corpus billing query retrieved the stray invoice deadline record because date tokens overlap. The model correctly abstained, but a request with no relevant billing evidence still incurred an API call. Use the parsed date as a temporal filter and exclude it from the lexical query. Keep unknown-start semantics explicit rather than masking this with a global transaction-time cutoff. See [retrieved evidence](16-retrieved-evidence.md).

## Informational: citation rules require semantic review

Every cited document ID exists. One answer cites an additional handover source outside its frozen source whitelist; that source does support the prior ownership. Conversely, a real scheduling source does not prove non-completion. Citation membership and expected-ID matching do not establish entailment. The report records both distinctions without changing the frozen expectations.

## Scope and limitations

- This is one live synthetic run with 13 distinct questions, not an official NVIDIA evaluation or a statistically reliable estimate of overall accuracy.
- Three cases also received independent uncached CLI requests. Other UI/CLI answer comparisons intentionally reuse cache; their matching prompt hashes verify shared retrieval while the independent subset checks fresh-model parity.
- Full Python and UI suites ran; headless Edge exercised the actual UI, slider, source popover, chat and egress panel.
- Malformed input and a real memory-server restart were checked. Provider-failure behavior was simulated rather than sending intentionally bad credentials to a real provider.
- Hermes Agent, Tavily, OpenShell/NemoClaw deployment and external-account ingestion were not exercised live. Their repository tests are included in the Python suite.
- The corpus is local Markdown, so live email, Slack and calendar collection is not demonstrated.
- The privacy audit covers the three synthetic full names and one synthetic email in this corpus. It does not prove exhaustive PII detection.
- State and response caches remain available under the ignored run folder for reproduction. API credentials are not copied into reports or traces. Historical global egress logs are preserved.
- The test backend uses a run-specific cache, egress log and a 16384-token budget via runtime setup. Those settings are disclosed in the setup report; source behavior is unchanged.

## Reproduce against the preserved test state

From the repository root in Command Prompt, load `.env` and serve the preserved state:

```cmd
.venv\Scripts\python.exe -m dotenv -f .env run -- .venv\Scripts\python.exe -m chronicle.memory serve --state .tmp/full-system-2026-10-18-1709/state
```

Use `CHRONICLE_MAX_TOKENS=16384` in that process. The normal command uses the normal user-profile response cache and egress log, whereas this evaluation deliberately isolated them. The disposable scripts under `.tmp/full-system-2026-10-18-1709/` reproduce the exact instrumented setup; rerunning `ingestion.py` or `answers.py` without clearing its state is a warm rerun, not a new cold test. Expected answers remain outside every corpus directory.
