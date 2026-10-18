# Live HTTP cold, HTTP warm and benchmark comparisons

Transport is the actual privacy-routed Nebius client. HTTP requests target a real Uvicorn server; CLI requests run the actual JSONL adapter in a separate process. Cache hits are confirmed by instrumenting provider transport, not inferred from latency.

## owner-before: http-cold

```json
{
  "id": "owner-before",
  "phase": "http-cold",
  "question": "Who owned the billing service on 2026-06-09?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Maya Patel",
    "source_ids": [
      "DEMO:billing-owner-0601",
      "DEMO:billing-handover-0610"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-owner-0601"
      },
      {
        "doc_id": "DEMO:billing-handover-0610"
      }
    ]
  },
  "seconds": 8.087,
  "provider_attempts": 1,
  "prompt_keys": [
    "55e2928352d711bc4556c30ed562f002b94a99ed764ac9abaccc851c3e053e8b"
  ]
}
```

## owner-before: http-warm

```json
{
  "id": "owner-before",
  "phase": "http-warm",
  "question": "Who owned the billing service on 2026-06-09?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Maya Patel",
    "source_ids": [
      "DEMO:billing-owner-0601",
      "DEMO:billing-handover-0610"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-owner-0601"
      },
      {
        "doc_id": "DEMO:billing-handover-0610"
      }
    ]
  },
  "seconds": 0.301,
  "provider_attempts": 0,
  "prompt_keys": [
    "55e2928352d711bc4556c30ed562f002b94a99ed764ac9abaccc851c3e053e8b"
  ]
}
```

## owner-before: cli-warm

```json
{
  "id": "owner-before",
  "phase": "cli-warm",
  "question": "Who owned the billing service on 2026-06-09?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "owner-before",
    "answer": "Maya Patel",
    "source_ids": [
      "DEMO:billing-owner-0601",
      "DEMO:billing-handover-0610"
    ]
  },
  "seconds": 2.57,
  "provider_attempts": 0,
  "prompt_keys": [
    "55e2928352d711bc4556c30ed562f002b94a99ed764ac9abaccc851c3e053e8b"
  ]
}
```

## owner-before: cli-uncached

```json
{
  "id": "owner-before",
  "phase": "cli-uncached",
  "question": "Who owned the billing service on 2026-06-09?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "owner-before",
    "answer": "Maya Patel",
    "source_ids": [
      "DEMO:billing-owner-0601",
      "DEMO:billing-handover-0610"
    ]
  },
  "seconds": 7.553,
  "provider_attempts": 1,
  "prompt_keys": [
    "55e2928352d711bc4556c30ed562f002b94a99ed764ac9abaccc851c3e053e8b"
  ]
}
```

## owner-boundary: http-cold

```json
{
  "id": "owner-boundary",
  "phase": "http-cold",
  "question": "Who owned the billing service on 2026-06-10?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Noah Williams",
    "source_ids": [
      "DEMO:billing-handover-0610"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-handover-0610"
      }
    ]
  },
  "seconds": 3.354,
  "provider_attempts": 1,
  "prompt_keys": [
    "451e88716f240bf99c2b6f56ad9a0592a1a11de43121c33ba3a50e9f31ffd371"
  ]
}
```

## owner-boundary: http-warm

```json
{
  "id": "owner-boundary",
  "phase": "http-warm",
  "question": "Who owned the billing service on 2026-06-10?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Noah Williams",
    "source_ids": [
      "DEMO:billing-handover-0610"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-handover-0610"
      }
    ]
  },
  "seconds": 0.296,
  "provider_attempts": 0,
  "prompt_keys": [
    "451e88716f240bf99c2b6f56ad9a0592a1a11de43121c33ba3a50e9f31ffd371"
  ]
}
```

## owner-boundary: cli-warm

```json
{
  "id": "owner-boundary",
  "phase": "cli-warm",
  "question": "Who owned the billing service on 2026-06-10?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "owner-boundary",
    "answer": "Noah Williams",
    "source_ids": [
      "DEMO:billing-handover-0610"
    ]
  },
  "seconds": 2.436,
  "provider_attempts": 0,
  "prompt_keys": [
    "451e88716f240bf99c2b6f56ad9a0592a1a11de43121c33ba3a50e9f31ffd371"
  ]
}
```

## owner-slider: http-cold

```json
{
  "id": "owner-slider",
  "phase": "http-cold",
  "question": "Who owns the billing service?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Noah Williams",
    "source_ids": [
      "DEMO:billing-handover-0610"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-handover-0610"
      }
    ]
  },
  "seconds": 3.074,
  "provider_attempts": 1,
  "prompt_keys": [
    "d2fcb62f9f910133badd3b6bdb74a9dde86e3596a31615561160e526329af033"
  ]
}
```

## owner-slider: http-warm

```json
{
  "id": "owner-slider",
  "phase": "http-warm",
  "question": "Who owns the billing service?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Noah Williams",
    "source_ids": [
      "DEMO:billing-handover-0610"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-handover-0610"
      }
    ]
  },
  "seconds": 0.272,
  "provider_attempts": 0,
  "prompt_keys": [
    "d2fcb62f9f910133badd3b6bdb74a9dde86e3596a31615561160e526329af033"
  ]
}
```

## owner-slider: cli-warm

```json
{
  "id": "owner-slider",
  "phase": "cli-warm",
  "question": "Who owns the billing service?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "owner-slider",
    "answer": "Noah Williams",
    "source_ids": [
      "DEMO:billing-handover-0610"
    ]
  },
  "seconds": 2.368,
  "provider_attempts": 0,
  "prompt_keys": [
    "d2fcb62f9f910133badd3b6bdb74a9dde86e3596a31615561160e526329af033"
  ]
}
```

## owner-named: http-cold

```json
{
  "id": "owner-named",
  "phase": "http-cold",
  "question": "Who owned billing on June 9?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Maya Patel",
    "source_ids": [
      "DEMO:billing-owner-0601"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-owner-0601"
      }
    ]
  },
  "seconds": 5.324,
  "provider_attempts": 1,
  "prompt_keys": [
    "4fabf76c68764fe17a6d8d9acb9e66144906bd1d4b3fd2a40aef413dd95277b2"
  ]
}
```

## owner-named: http-warm

```json
{
  "id": "owner-named",
  "phase": "http-warm",
  "question": "Who owned billing on June 9?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Maya Patel",
    "source_ids": [
      "DEMO:billing-owner-0601"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-owner-0601"
      }
    ]
  },
  "seconds": 0.295,
  "provider_attempts": 0,
  "prompt_keys": [
    "4fabf76c68764fe17a6d8d9acb9e66144906bd1d4b3fd2a40aef413dd95277b2"
  ]
}
```

## owner-named: cli-warm

```json
{
  "id": "owner-named",
  "phase": "cli-warm",
  "question": "Who owned billing on June 9?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "owner-named",
    "answer": "Maya Patel",
    "source_ids": [
      "DEMO:billing-owner-0601"
    ]
  },
  "seconds": 2.225,
  "provider_attempts": 0,
  "prompt_keys": [
    "4fabf76c68764fe17a6d8d9acb9e66144906bd1d4b3fd2a40aef413dd95277b2"
  ]
}
```

## owner-history: http-cold

```json
{
  "id": "owner-history",
  "phase": "http-cold",
  "question": "Who owned the billing service before Noah Williams?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Maya Patel",
    "source_ids": [
      "DEMO:billing-handover-0610",
      "DEMO:billing-owner-0601"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-handover-0610"
      },
      {
        "doc_id": "DEMO:billing-owner-0601"
      }
    ]
  },
  "seconds": 3.058,
  "provider_attempts": 1,
  "prompt_keys": [
    "1d966173a4fca81d4500129c2cc22739f44db1c8080de06ed62b99866bfc915c"
  ]
}
```

## owner-history: http-warm

```json
{
  "id": "owner-history",
  "phase": "http-warm",
  "question": "Who owned the billing service before Noah Williams?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Maya Patel",
    "source_ids": [
      "DEMO:billing-handover-0610",
      "DEMO:billing-owner-0601"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-handover-0610"
      },
      {
        "doc_id": "DEMO:billing-owner-0601"
      }
    ]
  },
  "seconds": 0.293,
  "provider_attempts": 0,
  "prompt_keys": [
    "1d966173a4fca81d4500129c2cc22739f44db1c8080de06ed62b99866bfc915c"
  ]
}
```

## owner-history: cli-warm

```json
{
  "id": "owner-history",
  "phase": "cli-warm",
  "question": "Who owned the billing service before Noah Williams?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "owner-history",
    "answer": "Maya Patel",
    "source_ids": [
      "DEMO:billing-handover-0610",
      "DEMO:billing-owner-0601"
    ]
  },
  "seconds": 2.353,
  "provider_attempts": 0,
  "prompt_keys": [
    "1d966173a4fca81d4500129c2cc22739f44db1c8080de06ed62b99866bfc915c"
  ]
}
```

## deadline-old: http-cold

```json
{
  "id": "deadline-old",
  "phase": "http-cold",
  "question": "What is the invoice export project deadline?",
  "as_of": "2026-06-05",
  "status": 200,
  "result": {
    "answer": "2026-06-18",
    "source_ids": [
      "DEMO:export-deadline-0603"
    ],
    "citations": [
      {
        "doc_id": "DEMO:export-deadline-0603"
      }
    ]
  },
  "seconds": 9.066,
  "provider_attempts": 1,
  "prompt_keys": [
    "862cd54a340ae3121b6ce2b68f75ac9886490f90930d2987f137281baf441acb"
  ]
}
```

## deadline-old: http-warm

```json
{
  "id": "deadline-old",
  "phase": "http-warm",
  "question": "What is the invoice export project deadline?",
  "as_of": "2026-06-05",
  "status": 200,
  "result": {
    "answer": "2026-06-18",
    "source_ids": [
      "DEMO:export-deadline-0603"
    ],
    "citations": [
      {
        "doc_id": "DEMO:export-deadline-0603"
      }
    ]
  },
  "seconds": 0.28,
  "provider_attempts": 0,
  "prompt_keys": [
    "862cd54a340ae3121b6ce2b68f75ac9886490f90930d2987f137281baf441acb"
  ]
}
```

## deadline-old: cli-warm

```json
{
  "id": "deadline-old",
  "phase": "cli-warm",
  "question": "What is the invoice export project deadline?",
  "as_of": "2026-06-05",
  "exit_code": 0,
  "result": {
    "id": "deadline-old",
    "answer": "2026-06-18",
    "source_ids": [
      "DEMO:export-deadline-0603"
    ]
  },
  "seconds": 2.475,
  "provider_attempts": 0,
  "prompt_keys": [
    "862cd54a340ae3121b6ce2b68f75ac9886490f90930d2987f137281baf441acb"
  ]
}
```

## deadline-new: http-cold

```json
{
  "id": "deadline-new",
  "phase": "http-cold",
  "question": "What is the invoice export project deadline?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "2026-06-25",
    "source_ids": [
      "DEMO:export-rescheduled-0612"
    ],
    "citations": [
      {
        "doc_id": "DEMO:export-rescheduled-0612"
      }
    ]
  },
  "seconds": 16.441,
  "provider_attempts": 1,
  "prompt_keys": [
    "eba2248cccf74e599bc996fb97022b1e8c22442d028ae0d77dbc1d0e34fa8b52"
  ]
}
```

## deadline-new: http-warm

```json
{
  "id": "deadline-new",
  "phase": "http-warm",
  "question": "What is the invoice export project deadline?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "2026-06-25",
    "source_ids": [
      "DEMO:export-rescheduled-0612"
    ],
    "citations": [
      {
        "doc_id": "DEMO:export-rescheduled-0612"
      }
    ]
  },
  "seconds": 0.271,
  "provider_attempts": 0,
  "prompt_keys": [
    "eba2248cccf74e599bc996fb97022b1e8c22442d028ae0d77dbc1d0e34fa8b52"
  ]
}
```

## deadline-new: cli-warm

```json
{
  "id": "deadline-new",
  "phase": "cli-warm",
  "question": "What is the invoice export project deadline?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "deadline-new",
    "answer": "2026-06-25",
    "source_ids": [
      "DEMO:export-rescheduled-0612"
    ]
  },
  "seconds": 2.689,
  "provider_attempts": 0,
  "prompt_keys": [
    "eba2248cccf74e599bc996fb97022b1e8c22442d028ae0d77dbc1d0e34fa8b52"
  ]
}
```

## deadline-new: cli-uncached

```json
{
  "id": "deadline-new",
  "phase": "cli-uncached",
  "question": "What is the invoice export project deadline?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "deadline-new",
    "answer": "2026-06-25",
    "source_ids": [
      "DEMO:export-rescheduled-0612"
    ]
  },
  "seconds": 7.75,
  "provider_attempts": 1,
  "prompt_keys": [
    "eba2248cccf74e599bc996fb97022b1e8c22442d028ae0d77dbc1d0e34fa8b52"
  ]
}
```

## search-owner: http-cold

```json
{
  "id": "search-owner",
  "phase": "http-cold",
  "question": "Who owns the search service?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Iris Chen",
    "source_ids": [
      "DEMO:search-owner-0615"
    ],
    "citations": [
      {
        "doc_id": "DEMO:search-owner-0615"
      }
    ]
  },
  "seconds": 2.556,
  "provider_attempts": 1,
  "prompt_keys": [
    "06dd79ef1958cbcbbb00708becf5a937e9cc4346f17ed38f0a6943dc831b21ad"
  ]
}
```

## search-owner: http-warm

```json
{
  "id": "search-owner",
  "phase": "http-warm",
  "question": "Who owns the search service?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Iris Chen",
    "source_ids": [
      "DEMO:search-owner-0615"
    ],
    "citations": [
      {
        "doc_id": "DEMO:search-owner-0615"
      }
    ]
  },
  "seconds": 0.294,
  "provider_attempts": 0,
  "prompt_keys": [
    "06dd79ef1958cbcbbb00708becf5a937e9cc4346f17ed38f0a6943dc831b21ad"
  ]
}
```

## search-owner: cli-warm

```json
{
  "id": "search-owner",
  "phase": "cli-warm",
  "question": "Who owns the search service?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "search-owner",
    "answer": "Iris Chen",
    "source_ids": [
      "DEMO:search-owner-0615"
    ]
  },
  "seconds": 2.596,
  "provider_attempts": 0,
  "prompt_keys": [
    "06dd79ef1958cbcbbb00708becf5a937e9cc4346f17ed38f0a6943dc831b21ad"
  ]
}
```

## email: http-cold

```json
{
  "id": "email",
  "phase": "http-cold",
  "question": "What is Maya Patel's work email?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "maya.patel@example.test",
    "source_ids": [
      "DEMO:billing-owner-0601"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-owner-0601"
      }
    ]
  },
  "seconds": 5.201,
  "provider_attempts": 1,
  "prompt_keys": [
    "bf521f856012962720fe4742f44164eb5a9a6155ccca5369dfa5d8a5391de5a3"
  ]
}
```

## email: http-warm

```json
{
  "id": "email",
  "phase": "http-warm",
  "question": "What is Maya Patel's work email?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "maya.patel@example.test",
    "source_ids": [
      "DEMO:billing-owner-0601"
    ],
    "citations": [
      {
        "doc_id": "DEMO:billing-owner-0601"
      }
    ]
  },
  "seconds": 0.287,
  "provider_attempts": 0,
  "prompt_keys": [
    "bf521f856012962720fe4742f44164eb5a9a6155ccca5369dfa5d8a5391de5a3"
  ]
}
```

## email: cli-warm

```json
{
  "id": "email",
  "phase": "cli-warm",
  "question": "What is Maya Patel's work email?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "email",
    "answer": "maya.patel@example.test",
    "source_ids": [
      "DEMO:billing-owner-0601"
    ]
  },
  "seconds": 2.52,
  "provider_attempts": 0,
  "prompt_keys": [
    "bf521f856012962720fe4742f44164eb5a9a6155ccca5369dfa5d8a5391de5a3"
  ]
}
```

## email: cli-uncached

```json
{
  "id": "email",
  "phase": "cli-uncached",
  "question": "What is Maya Patel's work email?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "email",
    "answer": "maya.patel@example.test",
    "source_ids": [
      "DEMO:billing-owner-0601"
    ]
  },
  "seconds": 7.775,
  "provider_attempts": 1,
  "prompt_keys": [
    "bf521f856012962720fe4742f44164eb5a9a6155ccca5369dfa5d8a5391de5a3"
  ]
}
```

## scheduled: http-cold

```json
{
  "id": "scheduled",
  "phase": "http-cold",
  "question": "When is the customer demo scheduled?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "2026-06-30",
    "source_ids": [
      "DEMO:demo-scheduled-0620"
    ],
    "citations": [
      {
        "doc_id": "DEMO:demo-scheduled-0620"
      }
    ]
  },
  "seconds": 3.347,
  "provider_attempts": 1,
  "prompt_keys": [
    "f41cace64e53538f74797a0fc04c6decef49a2b1d6e0206b4744e6dd865ecafc"
  ]
}
```

## scheduled: http-warm

```json
{
  "id": "scheduled",
  "phase": "http-warm",
  "question": "When is the customer demo scheduled?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "2026-06-30",
    "source_ids": [
      "DEMO:demo-scheduled-0620"
    ],
    "citations": [
      {
        "doc_id": "DEMO:demo-scheduled-0620"
      }
    ]
  },
  "seconds": 0.344,
  "provider_attempts": 0,
  "prompt_keys": [
    "f41cace64e53538f74797a0fc04c6decef49a2b1d6e0206b4744e6dd865ecafc"
  ]
}
```

## scheduled: cli-warm

```json
{
  "id": "scheduled",
  "phase": "cli-warm",
  "question": "When is the customer demo scheduled?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "scheduled",
    "answer": "2026-06-30",
    "source_ids": [
      "DEMO:demo-scheduled-0620"
    ]
  },
  "seconds": 2.434,
  "provider_attempts": 0,
  "prompt_keys": [
    "f41cace64e53538f74797a0fc04c6decef49a2b1d6e0206b4744e6dd865ecafc"
  ]
}
```

## not-completed: http-cold

```json
{
  "id": "not-completed",
  "phase": "http-cold",
  "question": "Has the customer demo been completed?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "No, the customer demo is scheduled for 2026-06-30 and has not been completed as of 2026-06-20.",
    "source_ids": [
      "DEMO:demo-scheduled-0620"
    ],
    "citations": [
      {
        "doc_id": "DEMO:demo-scheduled-0620"
      }
    ]
  },
  "seconds": 3.323,
  "provider_attempts": 1,
  "prompt_keys": [
    "35a77f5e114d31733dcc6048989acf2a7ec30bb0521b7ebea0e1c0b394e2006d"
  ]
}
```

## not-completed: http-warm

```json
{
  "id": "not-completed",
  "phase": "http-warm",
  "question": "Has the customer demo been completed?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "No, the customer demo is scheduled for 2026-06-30 and has not been completed as of 2026-06-20.",
    "source_ids": [
      "DEMO:demo-scheduled-0620"
    ],
    "citations": [
      {
        "doc_id": "DEMO:demo-scheduled-0620"
      }
    ]
  },
  "seconds": 0.301,
  "provider_attempts": 0,
  "prompt_keys": [
    "35a77f5e114d31733dcc6048989acf2a7ec30bb0521b7ebea0e1c0b394e2006d"
  ]
}
```

## not-completed: cli-warm

```json
{
  "id": "not-completed",
  "phase": "cli-warm",
  "question": "Has the customer demo been completed?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "not-completed",
    "answer": "No, the customer demo is scheduled for 2026-06-30 and has not been completed as of 2026-06-20.",
    "source_ids": [
      "DEMO:demo-scheduled-0620"
    ]
  },
  "seconds": 2.759,
  "provider_attempts": 0,
  "prompt_keys": [
    "35a77f5e114d31733dcc6048989acf2a7ec30bb0521b7ebea0e1c0b394e2006d"
  ]
}
```

## unknown: http-cold

```json
{
  "id": "unknown",
  "phase": "http-cold",
  "question": "What is the cafeteria lunch menu?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Not in the corpus",
    "source_ids": [],
    "citations": []
  },
  "seconds": 0.242,
  "provider_attempts": 0,
  "prompt_keys": []
}
```

## unknown: http-warm

```json
{
  "id": "unknown",
  "phase": "http-warm",
  "question": "What is the cafeteria lunch menu?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "Not in the corpus",
    "source_ids": [],
    "citations": []
  },
  "seconds": 0.221,
  "provider_attempts": 0,
  "prompt_keys": []
}
```

## unknown: cli-warm

```json
{
  "id": "unknown",
  "phase": "cli-warm",
  "question": "What is the cafeteria lunch menu?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "unknown",
    "answer": "Not in the corpus",
    "source_ids": []
  },
  "seconds": 0.333,
  "provider_attempts": 0,
  "prompt_keys": []
}
```

## before-corpus: http-cold

```json
{
  "id": "before-corpus",
  "phase": "http-cold",
  "question": "Who owned the billing service on 2026-05-31?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "The corpus does not contain any record of who owned the billing service as of 2026-05-31.",
    "source_ids": [],
    "citations": []
  },
  "seconds": 4.074,
  "provider_attempts": 1,
  "prompt_keys": [
    "0a5317e883548ae856c04f61cbf1d37c746c17513b6e8cb4f70ef4a55a3efe6e"
  ]
}
```

## before-corpus: http-warm

```json
{
  "id": "before-corpus",
  "phase": "http-warm",
  "question": "Who owned the billing service on 2026-05-31?",
  "as_of": "2026-06-20",
  "status": 200,
  "result": {
    "answer": "The corpus does not contain any record of who owned the billing service as of 2026-05-31.",
    "source_ids": [],
    "citations": []
  },
  "seconds": 0.288,
  "provider_attempts": 0,
  "prompt_keys": [
    "0a5317e883548ae856c04f61cbf1d37c746c17513b6e8cb4f70ef4a55a3efe6e"
  ]
}
```

## before-corpus: cli-warm

```json
{
  "id": "before-corpus",
  "phase": "cli-warm",
  "question": "Who owned the billing service on 2026-05-31?",
  "as_of": "2026-06-20",
  "exit_code": 0,
  "result": {
    "id": "before-corpus",
    "answer": "The corpus does not contain any record of who owned the billing service as of 2026-05-31.",
    "source_ids": []
  },
  "seconds": 2.534,
  "provider_attempts": 0,
  "prompt_keys": [
    "0a5317e883548ae856c04f61cbf1d37c746c17513b6e8cb4f70ef4a55a3efe6e"
  ]
}
```
