# Cold/warm and UI/benchmark comparison

13 cases were sent to HTTP cold, HTTP warm and the actual CLI adapter warm. Three cases also received an independent uncached CLI call. Warm parity alone could reuse the same answer, so the independent subset and prompt hashes are reported separately.

## Paired comparisons

```json
[
  {
    "id": "owner-before",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "owner-boundary",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "owner-slider",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "owner-named",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "owner-history",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "deadline-old",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "deadline-new",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "search-owner",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "email",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "scheduled",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "not-completed",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "unknown",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  },
  {
    "id": "before-corpus",
    "same_answer": true,
    "same_citations": true,
    "same_redacted_prompt_keys": true,
    "warm_http_identical": true,
    "warm_http_provider_attempts": 0,
    "warm_cli_provider_attempts": 0
  }
]
```

## Independent uncached CLI subset

```json
[
  {
    "id": "owner-before",
    "same_answer": true,
    "same_citations": true,
    "same_prompt_keys": true,
    "provider_attempts": 1
  },
  {
    "id": "deadline-new",
    "same_answer": true,
    "same_citations": true,
    "same_prompt_keys": true,
    "provider_attempts": 1
  },
  {
    "id": "email",
    "same_answer": true,
    "same_citations": true,
    "same_prompt_keys": true,
    "provider_attempts": 1
  }
]
```

## Latency and actual transport attempts

```json
{
  "http-cold": {
    "requests": 13,
    "mean_seconds": 5.165,
    "median_seconds": 3.354,
    "min_seconds": 0.242,
    "max_seconds": 16.441,
    "provider_attempts": 12
  },
  "http-warm": {
    "requests": 13,
    "mean_seconds": 0.288,
    "median_seconds": 0.293,
    "min_seconds": 0.221,
    "max_seconds": 0.344,
    "provider_attempts": 0
  },
  "cli-warm": {
    "requests": 13,
    "mean_seconds": 2.33,
    "median_seconds": 2.475,
    "min_seconds": 0.333,
    "max_seconds": 2.759,
    "provider_attempts": 0
  },
  "cli-uncached": {
    "requests": 3,
    "mean_seconds": 7.693,
    "median_seconds": 7.75,
    "min_seconds": 7.553,
    "max_seconds": 7.775,
    "provider_attempts": 3
  }
}
```

Cold here means an unseen prompt in the local model-response cache, not a newly launched server for every request. HTTP warm stays in the running server; each CLI measurement includes a fresh Python process and privacy-detector startup, so their wall times are not directly equivalent. The first HTTP request also pays initialization overhead.

## Live usage

```json
{
  "provider_attempts": 21,
  "phases": {
    "ingestion-cold": 6,
    "http-server": 12,
    "cli-uncached": 3
  },
  "reported_tokens": {
    "prompt_tokens": 11125,
    "completion_tokens": 41693,
    "total_tokens": 52818
  },
  "provider_errors": 0
}
```

Token totals include the six ingestion calls and independent CLI calls. They are provider-reported usage, not a dollar-cost estimate. Current model pricing and provider-side billing adjustments were not verified. Cached local completions are still appended to the egress log with zero tokens; transport instrumentation is the authoritative request count in this report.
