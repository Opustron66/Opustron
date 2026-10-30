# P2 memory and restart checks

```json
[
  {
    "day": "2026-06-09",
    "expected": "Maya Patel",
    "actual": "Maya Patel",
    "pass": true
  },
  {
    "day": "2026-06-10",
    "expected": "Noah Williams",
    "actual": "Noah Williams",
    "pass": true
  },
  {
    "day": "2026-06-20",
    "expected": "Noah Williams",
    "actual": "Noah Williams",
    "pass": true
  },
  {
    "check": "restart fact count",
    "expected": 8,
    "actual": 8,
    "pass": true
  }
]
```

## Stored facts and provenance

```json
[
  {
    "fact_id": "fact_a007f59d7b7d4436",
    "kind": "claim",
    "subject": "invoice export project",
    "predicate": "deadline",
    "object": "deadline",
    "content": "invoice export project deadline deadline",
    "valid_from": null,
    "valid_to": "2026-06-18",
    "event_at": null,
    "observed_at": "2026-06-12",
    "recorded_at": "2026-10-18T09:13:36.853800+00:00",
    "replaced_at": null,
    "superseded_by": null,
    "end_reason": "stated",
    "confidence": 1.0,
    "doc_id": "DEMO:export-rescheduled-0612",
    "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
    "sources": [
      {
        "doc_id": "DEMO:export-rescheduled-0612",
        "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
        "role": "closed",
        "observed_at": "2026-06-12",
        "valid_from": null,
        "valid_to": "2026-06-18",
        "confidence": 1.0,
        "uri": null
      }
    ]
  },
  {
    "fact_id": "fact_c2c57a00ea1241e6",
    "kind": "claim",
    "subject": "Maya Patel",
    "predicate": "status",
    "object": "maya.patel@example.test",
    "content": "Maya Patel status maya.patel@example.test",
    "valid_from": "2026-06-01",
    "valid_to": null,
    "event_at": null,
    "observed_at": "2026-06-01",
    "recorded_at": "2026-10-18T09:12:34.197398+00:00",
    "replaced_at": null,
    "superseded_by": null,
    "end_reason": null,
    "confidence": 1.0,
    "doc_id": "DEMO:billing-owner-0601",
    "quote": "Maya Patel's work email is maya.patel@example.test.",
    "sources": [
      {
        "doc_id": "DEMO:billing-owner-0601",
        "quote": "Maya Patel's work email is maya.patel@example.test.",
        "role": "opened",
        "observed_at": "2026-06-01",
        "valid_from": "2026-06-01",
        "valid_to": null,
        "confidence": 1.0,
        "uri": null
      }
    ]
  },
  {
    "fact_id": "fact_5bc36e986d854368",
    "kind": "claim",
    "subject": "Maya Patel",
    "predicate": "owns",
    "object": "billing service",
    "content": "Maya Patel owns billing service",
    "valid_from": "2026-06-01",
    "valid_to": "2026-06-10",
    "event_at": null,
    "observed_at": "2026-06-01",
    "recorded_at": "2026-10-18T09:13:36.840845+00:00",
    "replaced_at": null,
    "superseded_by": "fact_faec620537f540f2",
    "end_reason": "superseded",
    "confidence": 1.0,
    "doc_id": "DEMO:billing-owner-0601",
    "quote": "Effective 2026-06-01, Maya Patel owns the billing service.",
    "sources": [
      {
        "doc_id": "DEMO:billing-owner-0601",
        "quote": "Effective 2026-06-01, Maya Patel owns the billing service.",
        "role": "opened",
        "observed_at": "2026-06-01",
        "valid_from": "2026-06-01",
        "valid_to": null,
        "confidence": 1.0,
        "uri": null
      },
      {
        "doc_id": "DEMO:billing-handover-0610",
        "quote": "Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.",
        "role": "closed",
        "observed_at": "2026-06-10",
        "valid_from": null,
        "valid_to": "2026-06-10",
        "confidence": 1.0,
        "uri": null
      }
    ]
  },
  {
    "fact_id": "fact_52f14ccbff834cdf",
    "kind": "claim",
    "subject": "invoice export project",
    "predicate": "deadline",
    "object": "due",
    "content": "invoice export project deadline due on 2026-06-18",
    "valid_from": "2026-06-03",
    "valid_to": "2026-06-12",
    "event_at": "2026-06-18",
    "observed_at": "2026-06-03",
    "recorded_at": "2026-10-18T09:13:36.851618+00:00",
    "replaced_at": null,
    "superseded_by": "fact_e17371038ee74d6b",
    "end_reason": "superseded",
    "confidence": 1.0,
    "doc_id": "DEMO:export-deadline-0603",
    "quote": "The invoice export project is due on 2026-06-18.",
    "sources": [
      {
        "doc_id": "DEMO:export-deadline-0603",
        "quote": "The invoice export project is due on 2026-06-18.",
        "role": "opened",
        "observed_at": "2026-06-03",
        "valid_from": "2026-06-03",
        "valid_to": null,
        "confidence": 1.0,
        "uri": null
      }
    ]
  },
  {
    "fact_id": "fact_faec620537f540f2",
    "kind": "claim",
    "subject": "Noah Williams",
    "predicate": "owns",
    "object": "billing service",
    "content": "Noah Williams owns billing service",
    "valid_from": "2026-06-10",
    "valid_to": null,
    "event_at": null,
    "observed_at": "2026-06-10",
    "recorded_at": "2026-10-18T09:13:36.840845+00:00",
    "replaced_at": null,
    "superseded_by": null,
    "end_reason": null,
    "confidence": 1.0,
    "doc_id": "DEMO:billing-handover-0610",
    "quote": "Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.",
    "sources": [
      {
        "doc_id": "DEMO:billing-handover-0610",
        "quote": "Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.",
        "role": "opened",
        "observed_at": "2026-06-10",
        "valid_from": "2026-06-10",
        "valid_to": null,
        "confidence": 1.0,
        "uri": null
      }
    ]
  },
  {
    "fact_id": "fact_e17371038ee74d6b",
    "kind": "claim",
    "subject": "invoice export project",
    "predicate": "deadline",
    "object": "deadline",
    "content": "invoice export project deadline deadline on 2026-06-25",
    "valid_from": "2026-06-12",
    "valid_to": null,
    "event_at": "2026-06-25",
    "observed_at": "2026-06-12",
    "recorded_at": "2026-10-18T09:13:36.851618+00:00",
    "replaced_at": null,
    "superseded_by": null,
    "end_reason": null,
    "confidence": 1.0,
    "doc_id": "DEMO:export-rescheduled-0612",
    "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
    "sources": [
      {
        "doc_id": "DEMO:export-rescheduled-0612",
        "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
        "role": "opened",
        "observed_at": "2026-06-12",
        "valid_from": "2026-06-12",
        "valid_to": null,
        "confidence": 1.0,
        "uri": null
      }
    ]
  },
  {
    "fact_id": "fact_aa76308f8b914218",
    "kind": "claim",
    "subject": "Iris Chen",
    "predicate": "owns",
    "object": "search service",
    "content": "Iris Chen owns search service",
    "valid_from": "2026-06-15",
    "valid_to": null,
    "event_at": null,
    "observed_at": "2026-06-15",
    "recorded_at": "2026-10-18T09:13:36.854800+00:00",
    "replaced_at": null,
    "superseded_by": null,
    "end_reason": null,
    "confidence": 1.0,
    "doc_id": "DEMO:search-owner-0615",
    "quote": "Effective 2026-06-15, Iris Chen owns the search service.",
    "sources": [
      {
        "doc_id": "DEMO:search-owner-0615",
        "quote": "Effective 2026-06-15, Iris Chen owns the search service.",
        "role": "opened",
        "observed_at": "2026-06-15",
        "valid_from": "2026-06-15",
        "valid_to": null,
        "confidence": 1.0,
        "uri": null
      }
    ]
  },
  {
    "fact_id": "fact_70bfb4a970ae48d1",
    "kind": "claim",
    "subject": "customer demo",
    "predicate": "scheduled_for",
    "object": "scheduled",
    "content": "customer demo scheduled for scheduled on 2026-06-30",
    "valid_from": "2026-06-20",
    "valid_to": null,
    "event_at": "2026-06-30",
    "observed_at": "2026-06-20",
    "recorded_at": "2026-10-18T09:13:36.856826+00:00",
    "replaced_at": null,
    "superseded_by": null,
    "end_reason": null,
    "confidence": 1.0,
    "doc_id": "DEMO:demo-scheduled-0620",
    "quote": "The customer demo is scheduled for 2026-06-30",
    "sources": [
      {
        "doc_id": "DEMO:demo-scheduled-0620",
        "quote": "The customer demo is scheduled for 2026-06-30",
        "role": "opened",
        "observed_at": "2026-06-20",
        "valid_from": "2026-06-20",
        "valid_to": null,
        "confidence": 1.0,
        "uri": null
      }
    ]
  }
]
```

## Date snapshots

```json
{
  "2026-06-05": [
    {
      "fact_id": "fact_a007f59d7b7d4436",
      "kind": "claim",
      "subject": "invoice export project",
      "predicate": "deadline",
      "object": "deadline",
      "content": "invoice export project deadline deadline",
      "valid_from": null,
      "valid_to": "2026-06-18",
      "event_at": null,
      "observed_at": "2026-06-12",
      "recorded_at": "2026-10-18T09:13:36.853800+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": "stated",
      "confidence": 1.0,
      "doc_id": "DEMO:export-rescheduled-0612",
      "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
      "sources": [
        {
          "doc_id": "DEMO:export-rescheduled-0612",
          "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
          "role": "closed",
          "observed_at": "2026-06-12",
          "valid_from": null,
          "valid_to": "2026-06-18",
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_c2c57a00ea1241e6",
      "kind": "claim",
      "subject": "Maya Patel",
      "predicate": "status",
      "object": "maya.patel@example.test",
      "content": "Maya Patel status maya.patel@example.test",
      "valid_from": "2026-06-01",
      "valid_to": null,
      "event_at": null,
      "observed_at": "2026-06-01",
      "recorded_at": "2026-10-18T09:12:34.197398+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": null,
      "confidence": 1.0,
      "doc_id": "DEMO:billing-owner-0601",
      "quote": "Maya Patel's work email is maya.patel@example.test.",
      "sources": [
        {
          "doc_id": "DEMO:billing-owner-0601",
          "quote": "Maya Patel's work email is maya.patel@example.test.",
          "role": "opened",
          "observed_at": "2026-06-01",
          "valid_from": "2026-06-01",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_5bc36e986d854368",
      "kind": "claim",
      "subject": "Maya Patel",
      "predicate": "owns",
      "object": "billing service",
      "content": "Maya Patel owns billing service",
      "valid_from": "2026-06-01",
      "valid_to": "2026-06-10",
      "event_at": null,
      "observed_at": "2026-06-01",
      "recorded_at": "2026-10-18T09:13:36.840845+00:00",
      "replaced_at": null,
      "superseded_by": "fact_faec620537f540f2",
      "end_reason": "superseded",
      "confidence": 1.0,
      "doc_id": "DEMO:billing-owner-0601",
      "quote": "Effective 2026-06-01, Maya Patel owns the billing service.",
      "sources": [
        {
          "doc_id": "DEMO:billing-owner-0601",
          "quote": "Effective 2026-06-01, Maya Patel owns the billing service.",
          "role": "opened",
          "observed_at": "2026-06-01",
          "valid_from": "2026-06-01",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        },
        {
          "doc_id": "DEMO:billing-handover-0610",
          "quote": "Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.",
          "role": "closed",
          "observed_at": "2026-06-10",
          "valid_from": null,
          "valid_to": "2026-06-10",
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_52f14ccbff834cdf",
      "kind": "claim",
      "subject": "invoice export project",
      "predicate": "deadline",
      "object": "due",
      "content": "invoice export project deadline due on 2026-06-18",
      "valid_from": "2026-06-03",
      "valid_to": "2026-06-12",
      "event_at": "2026-06-18",
      "observed_at": "2026-06-03",
      "recorded_at": "2026-10-18T09:13:36.851618+00:00",
      "replaced_at": null,
      "superseded_by": "fact_e17371038ee74d6b",
      "end_reason": "superseded",
      "confidence": 1.0,
      "doc_id": "DEMO:export-deadline-0603",
      "quote": "The invoice export project is due on 2026-06-18.",
      "sources": [
        {
          "doc_id": "DEMO:export-deadline-0603",
          "quote": "The invoice export project is due on 2026-06-18.",
          "role": "opened",
          "observed_at": "2026-06-03",
          "valid_from": "2026-06-03",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    }
  ],
  "2026-06-09": [
    {
      "fact_id": "fact_a007f59d7b7d4436",
      "kind": "claim",
      "subject": "invoice export project",
      "predicate": "deadline",
      "object": "deadline",
      "content": "invoice export project deadline deadline",
      "valid_from": null,
      "valid_to": "2026-06-18",
      "event_at": null,
      "observed_at": "2026-06-12",
      "recorded_at": "2026-10-18T09:13:36.853800+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": "stated",
      "confidence": 1.0,
      "doc_id": "DEMO:export-rescheduled-0612",
      "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
      "sources": [
        {
          "doc_id": "DEMO:export-rescheduled-0612",
          "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
          "role": "closed",
          "observed_at": "2026-06-12",
          "valid_from": null,
          "valid_to": "2026-06-18",
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_c2c57a00ea1241e6",
      "kind": "claim",
      "subject": "Maya Patel",
      "predicate": "status",
      "object": "maya.patel@example.test",
      "content": "Maya Patel status maya.patel@example.test",
      "valid_from": "2026-06-01",
      "valid_to": null,
      "event_at": null,
      "observed_at": "2026-06-01",
      "recorded_at": "2026-10-18T09:12:34.197398+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": null,
      "confidence": 1.0,
      "doc_id": "DEMO:billing-owner-0601",
      "quote": "Maya Patel's work email is maya.patel@example.test.",
      "sources": [
        {
          "doc_id": "DEMO:billing-owner-0601",
          "quote": "Maya Patel's work email is maya.patel@example.test.",
          "role": "opened",
          "observed_at": "2026-06-01",
          "valid_from": "2026-06-01",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_5bc36e986d854368",
      "kind": "claim",
      "subject": "Maya Patel",
      "predicate": "owns",
      "object": "billing service",
      "content": "Maya Patel owns billing service",
      "valid_from": "2026-06-01",
      "valid_to": "2026-06-10",
      "event_at": null,
      "observed_at": "2026-06-01",
      "recorded_at": "2026-10-18T09:13:36.840845+00:00",
      "replaced_at": null,
      "superseded_by": "fact_faec620537f540f2",
      "end_reason": "superseded",
      "confidence": 1.0,
      "doc_id": "DEMO:billing-owner-0601",
      "quote": "Effective 2026-06-01, Maya Patel owns the billing service.",
      "sources": [
        {
          "doc_id": "DEMO:billing-owner-0601",
          "quote": "Effective 2026-06-01, Maya Patel owns the billing service.",
          "role": "opened",
          "observed_at": "2026-06-01",
          "valid_from": "2026-06-01",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        },
        {
          "doc_id": "DEMO:billing-handover-0610",
          "quote": "Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.",
          "role": "closed",
          "observed_at": "2026-06-10",
          "valid_from": null,
          "valid_to": "2026-06-10",
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_52f14ccbff834cdf",
      "kind": "claim",
      "subject": "invoice export project",
      "predicate": "deadline",
      "object": "due",
      "content": "invoice export project deadline due on 2026-06-18",
      "valid_from": "2026-06-03",
      "valid_to": "2026-06-12",
      "event_at": "2026-06-18",
      "observed_at": "2026-06-03",
      "recorded_at": "2026-10-18T09:13:36.851618+00:00",
      "replaced_at": null,
      "superseded_by": "fact_e17371038ee74d6b",
      "end_reason": "superseded",
      "confidence": 1.0,
      "doc_id": "DEMO:export-deadline-0603",
      "quote": "The invoice export project is due on 2026-06-18.",
      "sources": [
        {
          "doc_id": "DEMO:export-deadline-0603",
          "quote": "The invoice export project is due on 2026-06-18.",
          "role": "opened",
          "observed_at": "2026-06-03",
          "valid_from": "2026-06-03",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    }
  ],
  "2026-06-10": [
    {
      "fact_id": "fact_a007f59d7b7d4436",
      "kind": "claim",
      "subject": "invoice export project",
      "predicate": "deadline",
      "object": "deadline",
      "content": "invoice export project deadline deadline",
      "valid_from": null,
      "valid_to": "2026-06-18",
      "event_at": null,
      "observed_at": "2026-06-12",
      "recorded_at": "2026-10-18T09:13:36.853800+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": "stated",
      "confidence": 1.0,
      "doc_id": "DEMO:export-rescheduled-0612",
      "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
      "sources": [
        {
          "doc_id": "DEMO:export-rescheduled-0612",
          "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
          "role": "closed",
          "observed_at": "2026-06-12",
          "valid_from": null,
          "valid_to": "2026-06-18",
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_c2c57a00ea1241e6",
      "kind": "claim",
      "subject": "Maya Patel",
      "predicate": "status",
      "object": "maya.patel@example.test",
      "content": "Maya Patel status maya.patel@example.test",
      "valid_from": "2026-06-01",
      "valid_to": null,
      "event_at": null,
      "observed_at": "2026-06-01",
      "recorded_at": "2026-10-18T09:12:34.197398+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": null,
      "confidence": 1.0,
      "doc_id": "DEMO:billing-owner-0601",
      "quote": "Maya Patel's work email is maya.patel@example.test.",
      "sources": [
        {
          "doc_id": "DEMO:billing-owner-0601",
          "quote": "Maya Patel's work email is maya.patel@example.test.",
          "role": "opened",
          "observed_at": "2026-06-01",
          "valid_from": "2026-06-01",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_52f14ccbff834cdf",
      "kind": "claim",
      "subject": "invoice export project",
      "predicate": "deadline",
      "object": "due",
      "content": "invoice export project deadline due on 2026-06-18",
      "valid_from": "2026-06-03",
      "valid_to": "2026-06-12",
      "event_at": "2026-06-18",
      "observed_at": "2026-06-03",
      "recorded_at": "2026-10-18T09:13:36.851618+00:00",
      "replaced_at": null,
      "superseded_by": "fact_e17371038ee74d6b",
      "end_reason": "superseded",
      "confidence": 1.0,
      "doc_id": "DEMO:export-deadline-0603",
      "quote": "The invoice export project is due on 2026-06-18.",
      "sources": [
        {
          "doc_id": "DEMO:export-deadline-0603",
          "quote": "The invoice export project is due on 2026-06-18.",
          "role": "opened",
          "observed_at": "2026-06-03",
          "valid_from": "2026-06-03",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_faec620537f540f2",
      "kind": "claim",
      "subject": "Noah Williams",
      "predicate": "owns",
      "object": "billing service",
      "content": "Noah Williams owns billing service",
      "valid_from": "2026-06-10",
      "valid_to": null,
      "event_at": null,
      "observed_at": "2026-06-10",
      "recorded_at": "2026-10-18T09:13:36.840845+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": null,
      "confidence": 1.0,
      "doc_id": "DEMO:billing-handover-0610",
      "quote": "Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.",
      "sources": [
        {
          "doc_id": "DEMO:billing-handover-0610",
          "quote": "Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.",
          "role": "opened",
          "observed_at": "2026-06-10",
          "valid_from": "2026-06-10",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    }
  ],
  "2026-06-20": [
    {
      "fact_id": "fact_c2c57a00ea1241e6",
      "kind": "claim",
      "subject": "Maya Patel",
      "predicate": "status",
      "object": "maya.patel@example.test",
      "content": "Maya Patel status maya.patel@example.test",
      "valid_from": "2026-06-01",
      "valid_to": null,
      "event_at": null,
      "observed_at": "2026-06-01",
      "recorded_at": "2026-10-18T09:12:34.197398+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": null,
      "confidence": 1.0,
      "doc_id": "DEMO:billing-owner-0601",
      "quote": "Maya Patel's work email is maya.patel@example.test.",
      "sources": [
        {
          "doc_id": "DEMO:billing-owner-0601",
          "quote": "Maya Patel's work email is maya.patel@example.test.",
          "role": "opened",
          "observed_at": "2026-06-01",
          "valid_from": "2026-06-01",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_faec620537f540f2",
      "kind": "claim",
      "subject": "Noah Williams",
      "predicate": "owns",
      "object": "billing service",
      "content": "Noah Williams owns billing service",
      "valid_from": "2026-06-10",
      "valid_to": null,
      "event_at": null,
      "observed_at": "2026-06-10",
      "recorded_at": "2026-10-18T09:13:36.840845+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": null,
      "confidence": 1.0,
      "doc_id": "DEMO:billing-handover-0610",
      "quote": "Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.",
      "sources": [
        {
          "doc_id": "DEMO:billing-handover-0610",
          "quote": "Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.",
          "role": "opened",
          "observed_at": "2026-06-10",
          "valid_from": "2026-06-10",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_e17371038ee74d6b",
      "kind": "claim",
      "subject": "invoice export project",
      "predicate": "deadline",
      "object": "deadline",
      "content": "invoice export project deadline deadline on 2026-06-25",
      "valid_from": "2026-06-12",
      "valid_to": null,
      "event_at": "2026-06-25",
      "observed_at": "2026-06-12",
      "recorded_at": "2026-10-18T09:13:36.851618+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": null,
      "confidence": 1.0,
      "doc_id": "DEMO:export-rescheduled-0612",
      "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
      "sources": [
        {
          "doc_id": "DEMO:export-rescheduled-0612",
          "quote": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.",
          "role": "opened",
          "observed_at": "2026-06-12",
          "valid_from": "2026-06-12",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_aa76308f8b914218",
      "kind": "claim",
      "subject": "Iris Chen",
      "predicate": "owns",
      "object": "search service",
      "content": "Iris Chen owns search service",
      "valid_from": "2026-06-15",
      "valid_to": null,
      "event_at": null,
      "observed_at": "2026-06-15",
      "recorded_at": "2026-10-18T09:13:36.854800+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": null,
      "confidence": 1.0,
      "doc_id": "DEMO:search-owner-0615",
      "quote": "Effective 2026-06-15, Iris Chen owns the search service.",
      "sources": [
        {
          "doc_id": "DEMO:search-owner-0615",
          "quote": "Effective 2026-06-15, Iris Chen owns the search service.",
          "role": "opened",
          "observed_at": "2026-06-15",
          "valid_from": "2026-06-15",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    },
    {
      "fact_id": "fact_70bfb4a970ae48d1",
      "kind": "claim",
      "subject": "customer demo",
      "predicate": "scheduled_for",
      "object": "scheduled",
      "content": "customer demo scheduled for scheduled on 2026-06-30",
      "valid_from": "2026-06-20",
      "valid_to": null,
      "event_at": "2026-06-30",
      "observed_at": "2026-06-20",
      "recorded_at": "2026-10-18T09:13:36.856826+00:00",
      "replaced_at": null,
      "superseded_by": null,
      "end_reason": null,
      "confidence": 1.0,
      "doc_id": "DEMO:demo-scheduled-0620",
      "quote": "The customer demo is scheduled for 2026-06-30",
      "sources": [
        {
          "doc_id": "DEMO:demo-scheduled-0620",
          "quote": "The customer demo is scheduled for 2026-06-30",
          "role": "opened",
          "observed_at": "2026-06-20",
          "valid_from": "2026-06-20",
          "valid_to": null,
          "confidence": 1.0,
          "uri": null
        }
      ]
    }
  ]
}
```
