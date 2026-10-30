# Live browser checks

Headless Microsoft Edge, 1440 x 1000, Asia/Singapore timezone. Actual Vite UI, memory API, live answer service and run-specific egress server. Only the final error-path request is intercepted.

```json
{
  "checks": [
    {
      "check": "Real memory label",
      "pass": true,
      "detail": "\u25cf Live memory \u00b7 8 facts"
    },
    {
      "check": "Live egress label",
      "pass": true,
      "detail": null
    },
    {
      "check": "June 9 owner Maya",
      "pass": true,
      "detail": "UNKNOWN\nbilling service\nWHO OWNS\nMaya Patel\n1 Jun \u2192 10 Jun\nDEMO:billing-owner-0601\nNoah Williams\n10 Jun \u2192 now\nDEMO:billing-handover-0610"
    },
    {
      "check": "June 10 boundary owner Noah",
      "pass": true,
      "detail": "UNKNOWN\nbilling service\nWHO OWNS\nMaya Patel\n1 Jun \u2192 10 Jun\nDEMO:billing-owner-0601\nNoah Williams\n10 Jun \u2192 now\nDEMO:billing-handover-0610"
    },
    {
      "check": "June 20 owner Noah",
      "pass": true,
      "detail": "UNKNOWN\nbilling service\nWHO OWNS\nMaya Patel\n1 Jun \u2192 10 Jun\nDEMO:billing-owner-0601\nNoah Williams\n10 Jun \u2192 now\nDEMO:billing-handover-0610"
    },
    {
      "check": "Source quote popover",
      "pass": true,
      "detail": "\u00d7\n\nSource: DEMO:billing-owner-0601\n\n\"Effective 2026-06-01, Maya Patel owns the billing service.\""
    },
    {
      "check": "Real browser chat with explicit date overriding slider",
      "pass": true,
      "detail": {
        "answer": "Maya Patel",
        "source_ids": [
          "DEMO:billing-owner-0601"
        ],
        "citations": [
          {
            "doc_id": "DEMO:billing-owner-0601"
          }
        ]
      }
    },
    {
      "check": "Browser failure path",
      "pass": true,
      "detail": "Injected HTTP 502 in browser only; no provider call; no invented answer/citation."
    }
  ],
  "page_errors": []
}
```

Screenshots were captured locally at `.tmp/full-system-2026-10-18-1709/browser-live.png` and `browser-error.png`. They are ignored local artifacts and are not included in the reports-only PR; the observed browser results are recorded above.
