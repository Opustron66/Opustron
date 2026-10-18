# Cache failure regression

This diagnostic uses a synthetic transport, not a live paid call. It deliberately returns an empty response at 8192 tokens, then retries with 16384.

```json
{
  "fake_transport": true,
  "first_reply": "",
  "second_reply": "",
  "provider_budgets_observed": [
    8192
  ],
  "expected_budgets": [
    8192,
    16384
  ],
  "cache_bug_reproduced": true
}
```

The client caches an empty response before validation, and its key excludes the effective token budget. Therefore the larger-budget retry reuses the empty reply without another transport call. This confirms the previously observed defect; no source fix was applied during evaluation. The live run uses a 16384 budget from the start to avoid claiming an ineffective retry changed the provider budget.
