# Live staged ingestion

All calls use the privacy guard. Guard response caching is enabled for the initial cold run. No expected answers are provided to extraction.

## corpus-a, attempt 1

```json
{
  "stage": "corpus-a",
  "attempt": 1,
  "guard_cache": true,
  "seconds": 24.632,
  "documents": 2,
  "skipped": 0,
  "claims": 3,
  "failed": 0,
  "dropped": 0,
  "cache_hits": 0,
  "cache_misses": 2
}
```

## corpus-b, attempt 1

```json
{
  "stage": "corpus-b",
  "attempt": 1,
  "guard_cache": true,
  "seconds": 62.605,
  "documents": 4,
  "skipped": 0,
  "claims": 6,
  "failed": 0,
  "dropped": 0,
  "cache_hits": 0,
  "cache_misses": 4
}
```

## Repeated ingestion

```json
{
  "stage": "repeat-identical",
  "seconds": 0.007,
  "documents": 0,
  "skipped": 6,
  "claims": 0,
  "failed": 0,
  "dropped": 0,
  "cache_hits": 0,
  "cache_misses": 0
}
```

## New state with validated extraction cache

```json
{
  "documents": 6,
  "skipped": 0,
  "claims": 9,
  "failed": 0,
  "dropped": 0,
  "cache_hits": 6,
  "cache_misses": 0
}
```

## Extracted claims

```json
[
  {
    "subject": "Maya Patel",
    "predicate": "owns",
    "object": "billing service",
    "valid_from": "2026-06-01",
    "valid_to": null,
    "observed_at": "2026-06-01",
    "doc_id": "DEMO:billing-owner-0601",
    "quote": "Effective 2026-06-01, Maya Patel owns the billing service.",
    "confidence": 1.0
  },
  {
    "subject": "Maya Patel",
    "predicate": "status",
    "object": "maya.patel@example.test",
    "valid_from": "2026-06-01",
    "valid_to": null,
    "observed_at": "2026-06-01",
    "doc_id": "DEMO:billing-owner-0601",
    "quote": "Maya Patel's work email is maya.patel@example.test.",
    "confidence": 1.0
  },
  {
    "subject": "invoice export project",
    "predicate": "deadline",
    "object": "due",
    "valid_from": "2026-06-18",
    "valid_to": null,
    "observed_at": "2026-06-03",
    "doc_id": "DEMO:export-deadline-0603",
    "quote": "The invoice export project is due on 2026-06-18.",
    "confidence": 1.0
  },
  {
    "subject": "Noah Williams",
    "predicate": "owns",
    "object": "billing service",
    "valid_from": "2026-06-10",
    "valid_to": null,
    "observed_at": "2026-06-10",
    "doc_id": "DEMO:billing-handover-0610",
    "quote": "Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.",
    "confidence": 1.0
  },
  {
    "subject": "Maya Patel",
    "predicate": "owns",
    "object": "billing service",
    "valid_from": null,
    "valid_to": "2026-06-10",
    "observed_at": "2026-06-10",
    "doc_id": "DEMO:billing-handover-0610",
    "quote": "Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.",
    "confidence": 1.0
  },
  {
    "subject": "invoice export project",
    "predicate": "deadline",
    "object": "deadline",
    "valid_from": "2026-06-25",
    "valid_to": null,
    "observed_at": "2026-06-12",
    "doc_id": "DEMO:export-rescheduled-0612",
    "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
    "confidence": 1.0
  },
  {
    "subject": "invoice export project",
    "predicate": "deadline",
    "object": "deadline",
    "valid_from": null,
    "valid_to": "2026-06-18",
    "observed_at": "2026-06-12",
    "doc_id": "DEMO:export-rescheduled-0612",
    "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
    "confidence": 1.0
  },
  {
    "subject": "Iris Chen",
    "predicate": "owns",
    "object": "search service",
    "valid_from": "2026-06-15",
    "valid_to": null,
    "observed_at": "2026-06-15",
    "doc_id": "DEMO:search-owner-0615",
    "quote": "Effective 2026-06-15, Iris Chen owns the search service.",
    "confidence": 1.0
  },
  {
    "subject": "customer demo",
    "predicate": "scheduled_for",
    "object": "scheduled",
    "valid_from": "2026-06-30",
    "valid_to": null,
    "observed_at": "2026-06-20",
    "doc_id": "DEMO:demo-scheduled-0620",
    "quote": "The customer demo is scheduled for 2026-06-30",
    "confidence": 1.0
  }
]
```
