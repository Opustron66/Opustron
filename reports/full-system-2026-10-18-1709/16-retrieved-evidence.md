# Exact shared retrieval evidence

Replayed against the unchanged stored facts without calling a model. Both UI and CLI call this same retrieval implementation. Prompt-key parity is separately verified in the comparison report.

```json
[
  {
    "id": "owner-before",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-06-09"
    },
    "evidence": [
      {
        "doc_id": "DEMO:billing-owner-0601",
        "date": "2026-06-01",
        "score": 4.28915867170136,
        "text": "{\"subject\": \"Maya Patel\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-01\", \"doc_id\": \"DEMO:billing-owner-0601\", \"quote\": \"Effective 2026-06-01, Maya Patel owns the billing service.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:billing-handover-0610",
        "date": "2026-06-10",
        "score": 4.28915867170136,
        "text": "{\"subject\": \"Maya Patel\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:export-deadline-0603",
        "date": "2026-06-03",
        "score": 0.5241758129836019,
        "text": "{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"due\", \"valid_from\": \"2026-06-18\", \"valid_to\": \"2026-06-12\", \"observed_at\": \"2026-06-03\", \"doc_id\": \"DEMO:export-deadline-0603\", \"quote\": \"The invoice export project is due on 2026-06-18.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:export-rescheduled-0612",
        "date": "2026-06-12",
        "score": 0.5166905574233442,
        "text": "{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": \"2026-06-18\", \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}"
      }
    ]
  },
  {
    "id": "owner-boundary",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-06-10"
    },
    "evidence": [
      {
        "doc_id": "DEMO:billing-handover-0610",
        "date": "2026-06-10",
        "score": 4.042395656634888,
        "text": "{\"subject\": \"Noah Williams\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:export-deadline-0603",
        "date": "2026-06-03",
        "score": 0.5132190243249231,
        "text": "{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"due\", \"valid_from\": \"2026-06-18\", \"valid_to\": \"2026-06-12\", \"observed_at\": \"2026-06-03\", \"doc_id\": \"DEMO:export-deadline-0603\", \"quote\": \"The invoice export project is due on 2026-06-18.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:export-rescheduled-0612",
        "date": "2026-06-12",
        "score": 0.5053902595470853,
        "text": "{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": \"2026-06-18\", \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}"
      }
    ]
  },
  {
    "id": "owner-slider",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-06-20"
    },
    "evidence": [
      {
        "doc_id": "DEMO:billing-handover-0610",
        "date": "2026-06-10",
        "score": 4.594610856150723,
        "text": "{\"subject\": \"Noah Williams\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:search-owner-0615",
        "date": "2026-06-15",
        "score": 2.790905114940299,
        "text": "{\"subject\": \"Iris Chen\", \"predicate\": \"owns\", \"object\": \"search service\", \"valid_from\": \"2026-06-15\", \"valid_to\": null, \"observed_at\": \"2026-06-15\", \"doc_id\": \"DEMO:search-owner-0615\", \"quote\": \"Effective 2026-06-15, Iris Chen owns the search service.\", \"confidence\": 1.0}"
      }
    ]
  },
  {
    "id": "owner-named",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-06-09"
    },
    "evidence": [
      {
        "doc_id": "DEMO:billing-owner-0601",
        "date": "2026-06-01",
        "score": 1.9213059564773078,
        "text": "{\"subject\": \"Maya Patel\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-01\", \"doc_id\": \"DEMO:billing-owner-0601\", \"quote\": \"Effective 2026-06-01, Maya Patel owns the billing service.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:billing-handover-0610",
        "date": "2026-06-10",
        "score": 1.9213059564773078,
        "text": "{\"subject\": \"Maya Patel\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.\", \"confidence\": 1.0}"
      }
    ]
  },
  {
    "id": "owner-history",
    "plan": {
      "kind": "ordering_or_history",
      "reference_date": "None"
    },
    "evidence": [
      {
        "doc_id": "DEMO:billing-handover-0610",
        "date": "2026-06-10",
        "score": 7.356897039356268,
        "text": "{\"subject\": \"Noah Williams\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.\", \"confidence\": 1.0}\n{\"subject\": \"Maya Patel\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:billing-owner-0601",
        "date": "2026-06-01",
        "score": 5.626706774344877,
        "text": "{\"subject\": \"Maya Patel\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-01\", \"doc_id\": \"DEMO:billing-owner-0601\", \"quote\": \"Effective 2026-06-01, Maya Patel owns the billing service.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:search-owner-0615",
        "date": "2026-06-15",
        "score": 1.5184036634441382,
        "text": "{\"subject\": \"Iris Chen\", \"predicate\": \"owns\", \"object\": \"search service\", \"valid_from\": \"2026-06-15\", \"valid_to\": null, \"observed_at\": \"2026-06-15\", \"doc_id\": \"DEMO:search-owner-0615\", \"quote\": \"Effective 2026-06-15, Iris Chen owns the search service.\", \"confidence\": 1.0}"
      }
    ]
  },
  {
    "id": "deadline-old",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-06-05"
    },
    "evidence": [
      {
        "doc_id": "DEMO:export-rescheduled-0612",
        "date": "2026-06-12",
        "score": 4.66224609290203,
        "text": "{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": \"2026-06-18\", \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:export-deadline-0603",
        "date": "2026-06-03",
        "score": 4.454914994111011,
        "text": "{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"due\", \"valid_from\": \"2026-06-18\", \"valid_to\": \"2026-06-12\", \"observed_at\": \"2026-06-03\", \"doc_id\": \"DEMO:export-deadline-0603\", \"quote\": \"The invoice export project is due on 2026-06-18.\", \"confidence\": 1.0}"
      }
    ]
  },
  {
    "id": "deadline-new",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-06-20"
    },
    "evidence": [
      {
        "doc_id": "DEMO:export-rescheduled-0612",
        "date": "2026-06-12",
        "score": 9.01429768982613,
        "text": "{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": \"2026-06-25\", \"valid_to\": null, \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}"
      }
    ]
  },
  {
    "id": "search-owner",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-06-20"
    },
    "evidence": [
      {
        "doc_id": "DEMO:search-owner-0615",
        "date": "2026-06-15",
        "score": 5.000587687362291,
        "text": "{\"subject\": \"Iris Chen\", \"predicate\": \"owns\", \"object\": \"search service\", \"valid_from\": \"2026-06-15\", \"valid_to\": null, \"observed_at\": \"2026-06-15\", \"doc_id\": \"DEMO:search-owner-0615\", \"quote\": \"Effective 2026-06-15, Iris Chen owns the search service.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:billing-handover-0610",
        "date": "2026-06-10",
        "score": 2.4856736897662084,
        "text": "{\"subject\": \"Noah Williams\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.\", \"confidence\": 1.0}"
      }
    ]
  },
  {
    "id": "email",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-06-20"
    },
    "evidence": [
      {
        "doc_id": "DEMO:billing-owner-0601",
        "date": "2026-06-01",
        "score": 5.682809383347603,
        "text": "{\"subject\": \"Maya Patel\", \"predicate\": \"status\", \"object\": \"maya.patel@example.test\", \"valid_from\": \"2026-06-01\", \"valid_to\": null, \"observed_at\": \"2026-06-01\", \"doc_id\": \"DEMO:billing-owner-0601\", \"quote\": \"Maya Patel's work email is maya.patel@example.test.\", \"confidence\": 1.0}"
      },
      {
        "doc_id": "DEMO:billing-handover-0610",
        "date": "2026-06-10",
        "score": 1.6472635452843118,
        "text": "{\"subject\": \"Noah Williams\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, Noah Williams takes over ownership of the billing service from Maya Patel.\", \"confidence\": 1.0}"
      }
    ]
  },
  {
    "id": "scheduled",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-06-20"
    },
    "evidence": [
      {
        "doc_id": "DEMO:demo-scheduled-0620",
        "date": "2026-06-20",
        "score": 7.207049969776923,
        "text": "{\"subject\": \"customer demo\", \"predicate\": \"scheduled_for\", \"object\": \"scheduled\", \"valid_from\": \"2026-06-30\", \"valid_to\": null, \"observed_at\": \"2026-06-20\", \"doc_id\": \"DEMO:demo-scheduled-0620\", \"quote\": \"The customer demo is scheduled for 2026-06-30\", \"confidence\": 1.0}"
      }
    ]
  },
  {
    "id": "not-completed",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-06-20"
    },
    "evidence": [
      {
        "doc_id": "DEMO:demo-scheduled-0620",
        "date": "2026-06-20",
        "score": 4.641072426357894,
        "text": "{\"subject\": \"customer demo\", \"predicate\": \"scheduled_for\", \"object\": \"scheduled\", \"valid_from\": \"2026-06-30\", \"valid_to\": null, \"observed_at\": \"2026-06-20\", \"doc_id\": \"DEMO:demo-scheduled-0620\", \"quote\": \"The customer demo is scheduled for 2026-06-30\", \"confidence\": 1.0}"
      }
    ]
  },
  {
    "id": "unknown",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-06-20"
    },
    "evidence": []
  },
  {
    "id": "before-corpus",
    "plan": {
      "kind": "as_of",
      "reference_date": "2026-05-31"
    },
    "evidence": [
      {
        "doc_id": "DEMO:export-rescheduled-0612",
        "date": "2026-06-12",
        "score": 0.39556284962119864,
        "text": "{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": \"2026-06-18\", \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}"
      }
    ]
  }
]
```
