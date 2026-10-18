# Run setup

- Local date: 18 October 2026, Asia/Singapore.
- Branch: main
- Commit: 359f813c28debfadb2b6c7f00ab56005e704cb47
- Python: 3.12.9
- Executable: `C:\Github Projects\Opustron\.venv\Scripts\python.exe`
- Source working tree was clean at start. Source code will not be modified.
- Model: nvidia/Nemotron-3_5-Lightning (will confirm actual configured value before live calls).
- Test token budget: 16384; temperature: shared client default 0.
- Request timeout: 180 seconds; ingestion workers: 1.
- Historical global egress log is preserved. Run-specific egress, transport metadata and caches are isolated under `.tmp/full-system-2026-10-18-1709/`.
- Cleared prior `.tmp/accuracy-smoke` and user-profile `.chronicle/llm_cache`. No Chronicle servers were running.
- New state is `.tmp/full-system-2026-10-18-1709/state`. Expected answers are never placed in the corpus or sent to the answer model.
- Browser tooling is installed separately under ignored `.tmp/full-system-tools`, using headless Edge.

## Completion audit

- All 19 Markdown reports were scanned for configured API-key/token/secret values: no matches.
- Evaluation API, egress and Vite processes were stopped after the restart check. No pre-existing user servers were stopped during the final cleanup.
- The preserved run state and caches are under `.tmp/full-system-2026-10-18-1709/`.
- Final Git status contains only the new `reports/` directory; product source files remain unchanged. At evaluation completion, reports were still local; the later reports-only PR does not change the tested product source.
- `git diff --check` passed for tracked files. Frozen evidence and expectations were not edited during grading.

## Corpus snapshot

### 01-billing-owner.md

SHA256: `d313876ab405a2f38f6f56d62c2dc446691d01a79d1a44771c3d16927a275ceb`

```markdown
---
doc_id: DEMO:billing-owner-0601
date: 2026-06-01
subject: Billing ownership
---

Effective 2026-06-01, Maya Patel owns the billing service.
Maya Patel's work email is maya.patel@example.test.

```

### 02-export-deadline.md

SHA256: `7882e740124259e8140f2e31edb57d6509a992176732db40788a365b6c3f1222`

```markdown
---
doc_id: DEMO:export-deadline-0603
date: 2026-06-03
subject: Invoice export deadline
---

The invoice export project is due on 2026-06-18.

```

### 03-billing-handover.md

SHA256: `4d709f6d291239c1ddeccf746bfbbeb61a4972d9b66e08e7b01052405408aa07`

```markdown
---
doc_id: DEMO:billing-handover-0610
date: 2026-06-10
subject: Billing ownership handover
---

Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.
Maya Patel no longer owns the billing service from 2026-06-10 onward.

```

### 04-export-rescheduled.md

SHA256: `bc2bd07a79090e8ccb2f64dc71f1703a746111390f7b4c499073f148685e984b`

```markdown
---
doc_id: DEMO:export-rescheduled-0612
date: 2026-06-12
subject: Invoice export deadline change
---

The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.
The old deadline of 2026-06-18 is no longer in effect.

```

### 05-search-owner.md

SHA256: `33f79a379d0f45c0f3d3f78925f8d93f84c045db6781195dd67b59a0497903b9`

```markdown
---
doc_id: DEMO:search-owner-0615
date: 2026-06-15
subject: Search ownership
---

Effective 2026-06-15, Iris Chen owns the search service.

```

### 06-demo-scheduled.md

SHA256: `fc4fb8b8cea273b45c24b98be68eaf6d0bacd79102046068466fa0f67ad2f9c0`

```markdown
---
doc_id: DEMO:demo-scheduled-0620
date: 2026-06-20
subject: Customer demo scheduling
---

The customer demo is scheduled for 2026-06-30.
This message confirms the schedule only; it does not report a completed demo.

```
