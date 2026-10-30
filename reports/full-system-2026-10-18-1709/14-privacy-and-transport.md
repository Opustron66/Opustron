# Privacy and provider transport audit

The test wrapper observes arguments at the existing guard client transport boundary, after redaction. It does not bypass the privacy router. API credentials and HTTP authorization headers are never recorded. Raw reasoning text is not recorded.

```json
{
  "live_transport_attempts": 21,
  "raw_synthetic_identifier_occurrences_by_request": {
    "Maya Patel": 0,
    "Noah Williams": 0,
    "Iris Chen": 0,
    "maya.patel@example.test": 0
  },
  "requests_with_person_tokens": 15,
  "requests_with_email_tokens": 3,
  "requests_retaining_2026_dates": 21,
  "run_egress_records": 47,
  "redacted_egress_records": 31
}
```

The synthetic full names and email above never appeared in outbound messages. Dates remained usable. The email answer was restored to the original value, demonstrating the re-identification path. This audit covers only the identifiers in this corpus; it is not proof that every possible name/PII string is detected. Cached local calls also produce egress records, so these records must not be equated with actual network requests.

## Transport trace (redacted prompts, completion metadata and provider usage)

```json
[
  {
    "phase": "ingestion-cold",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "You extract atomic factual claims from one document.\nThe document was written on 2026-06-01. Resolve every relative date (\"next Friday\", \"yesterday\")\nagainst THAT date, never today's date. Output ONLY JSON: {\"claims\": [...]} with no commentary.\nEach claim: subject, predicate, object, valid_from, valid_to, quote, confidence (0-1).\n- One fact per claim. Subject/object are canonical entity names (no pronouns).\n- predicate: one of ['owns', 'works_on', 'works_at', 'ORG_1', 'status', 'deadline', 'scheduled_for', 'located_in', 'decided', 'proposed', 'completed', 'blocked_by', 'member_of', 'role', 'related_to'] (use related_to only if nothing fits).\n- valid_from / valid_to: the date expression exactly as written in the text (e.g. \"next Friday\",\n  \"2026-05-12\", \"today\") or null. valid_from = when the fact starts being true; valid_to = when it ends.\n- Deadlines and scheduled events: subject = the thing, predicate = deadline/scheduled_for,\n  object = a short description of what is due or happening (NOT the date), and the date goes in\n  valid_from. Example: \"The migration is due next Friday\" -> subject \"migration\", predicate\n  \"deadline\", object \"due\", valid_from \"next Friday\", PERSON_1.\n- Changes of ownership/role (takeovers, handovers, reassignments) need TWO claims:\n  1. the NEW state: new person, predicate owns (or role/works_on), the thing, valid_from = the\n     effective date (\"today\" if \"effective today\"), valid_to null;\n  2. the LOC_1 state ending: old person, same predicate, same thing, valid_from null, valid_to = the\n     same effective date.\n  Example: \"Effective today, PERSON_2 takes over payments from ORG_2\" -> (PERSON_2, owns, payments,\n  valid_from \"today\", null) and (ORG_2, owns, payments, null, valid_to \"today\").\n- quote: a ORG_3 span copied from the document that supports the claim; reuse the same quote\n  for both claims of a change.\n- Include who proposed vs who did when the text distinguishes them (predicate proposed vs completed).\n- Do not invent facts the document does not state. If there are none, return {\"claims\": []}."
      },
      {
        "role": "user",
        "content": "Effective 2026-06-01, PERSON_3 owns the billing service.\nPERSON_4 work email is EMAIL_1.\n"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 387,
    "reasoning_length": 11342,
    "usage": {
      "completion_tokens": 3368,
      "prompt_tokens": 603,
      "total_tokens": 3971,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 3219,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 603
    },
    "seconds": 11.579
  },
  {
    "phase": "ingestion-cold",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "You extract atomic factual claims from one document.\nThe document was written on 2026-06-03. Resolve every relative date (\"next Friday\", \"yesterday\")\nagainst THAT date, never today's date. Output ONLY JSON: {\"claims\": [...]} with no commentary.\nEach claim: subject, predicate, object, valid_from, valid_to, quote, confidence (0-1).\n- One fact per claim. Subject/object are canonical entity names (no pronouns).\n- predicate: one of ['owns', 'works_on', 'works_at', 'ORG_1', 'status', 'deadline', 'scheduled_for', 'located_in', 'decided', 'proposed', 'completed', 'blocked_by', 'member_of', 'role', 'related_to'] (use related_to only if nothing fits).\n- valid_from / valid_to: the date expression exactly as written in the text (e.g. \"next Friday\",\n  \"2026-05-12\", \"today\") or null. valid_from = when the fact starts being true; valid_to = when it ends.\n- Deadlines and scheduled events: subject = the thing, predicate = deadline/scheduled_for,\n  object = a short description of what is due or happening (NOT the date), and the date goes in\n  valid_from. Example: \"The migration is due next Friday\" -> subject \"migration\", predicate\n  \"deadline\", object \"due\", valid_from \"next Friday\", PERSON_1.\n- Changes of ownership/role (takeovers, handovers, reassignments) need TWO claims:\n  1. the NEW state: new person, predicate owns (or role/works_on), the thing, valid_from = the\n     effective date (\"today\" if \"effective today\"), valid_to null;\n  2. the LOC_1 state ending: old person, same predicate, same thing, valid_from null, valid_to = the\n     same effective date.\n  Example: \"Effective today, PERSON_2 takes over payments from ORG_2\" -> (PERSON_2, owns, payments,\n  valid_from \"today\", null) and (ORG_2, owns, payments, null, valid_to \"today\").\n- quote: a ORG_3 span copied from the document that supports the claim; reuse the same quote\n  for both claims of a change.\n- Include who proposed vs who did when the text distinguishes them (predicate proposed vs completed).\n- Do not invent facts the document does not state. If there are none, return {\"claims\": []}."
      },
      {
        "role": "user",
        "content": "The invoice export project is due on 2026-06-18.\n"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 217,
    "reasoning_length": 4006,
    "usage": {
      "completion_tokens": 1207,
      "prompt_tokens": 587,
      "total_tokens": 1794,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 1125,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 587
    },
    "seconds": 4.416
  },
  {
    "phase": "ingestion-cold",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "You extract atomic factual claims from one document.\nThe document was written on 2026-06-10. Resolve every relative date (\"next Friday\", \"yesterday\")\nagainst THAT date, never today's date. Output ONLY JSON: {\"claims\": [...]} with no commentary.\nEach claim: subject, predicate, object, valid_from, valid_to, quote, confidence (0-1).\n- One fact per claim. Subject/object are canonical entity names (no pronouns).\n- predicate: one of ['owns', 'works_on', 'works_at', 'ORG_1', 'status', 'deadline', 'scheduled_for', 'located_in', 'decided', 'proposed', 'completed', 'blocked_by', 'member_of', 'role', 'related_to'] (use related_to only if nothing fits).\n- valid_from / valid_to: the date expression exactly as written in the text (e.g. \"next Friday\",\n  \"2026-05-12\", \"today\") or null. valid_from = when the fact starts being true; valid_to = when it ends.\n- Deadlines and scheduled events: subject = the thing, predicate = deadline/scheduled_for,\n  object = a short description of what is due or happening (NOT the date), and the date goes in\n  valid_from. Example: \"The migration is due next Friday\" -> subject \"migration\", predicate\n  \"deadline\", object \"due\", valid_from \"next Friday\", PERSON_1.\n- Changes of ownership/role (takeovers, handovers, reassignments) need TWO claims:\n  1. the NEW state: new person, predicate owns (or role/works_on), the thing, valid_from = the\n     effective date (\"today\" if \"effective today\"), valid_to null;\n  2. the LOC_1 state ending: old person, same predicate, same thing, valid_from null, valid_to = the\n     same effective date.\n  Example: \"Effective today, PERSON_2 takes over payments from ORG_2\" -> (PERSON_2, owns, payments,\n  valid_from \"today\", null) and (ORG_2, owns, payments, null, valid_to \"today\").\n- quote: a ORG_3 span copied from the document that supports the claim; reuse the same quote\n  for both claims of a change.\n- Include who proposed vs who did when the text distinguishes them (predicate proposed vs completed).\n- Do not invent facts the document does not state. If there are none, return {\"claims\": []}."
      },
      {
        "role": "user",
        "content": "Effective today, 2026-06-10, PERSON_3 takes over ownership of the billing service from PERSON_4.\nPERSON_4 no longer owns the billing service from 2026-06-10 onward.\n"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 510,
    "reasoning_length": 7076,
    "usage": {
      "completion_tokens": 2380,
      "prompt_tokens": 625,
      "total_tokens": 3005,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 2186,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 625
    },
    "seconds": 7.582
  },
  {
    "phase": "ingestion-cold",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "You extract atomic factual claims from one document.\nThe document was written on 2026-06-12. Resolve every relative date (\"next Friday\", \"yesterday\")\nagainst THAT date, never today's date. Output ONLY JSON: {\"claims\": [...]} with no commentary.\nEach claim: subject, predicate, object, valid_from, valid_to, quote, confidence (0-1).\n- One fact per claim. Subject/object are canonical entity names (no pronouns).\n- predicate: one of ['owns', 'works_on', 'works_at', 'ORG_1', 'status', 'deadline', 'scheduled_for', 'located_in', 'decided', 'proposed', 'completed', 'blocked_by', 'member_of', 'role', 'related_to'] (use related_to only if nothing fits).\n- valid_from / valid_to: the date expression exactly as written in the text (e.g. \"next Friday\",\n  \"2026-05-12\", \"today\") or null. valid_from = when the fact starts being true; valid_to = when it ends.\n- Deadlines and scheduled events: subject = the thing, predicate = deadline/scheduled_for,\n  object = a short description of what is due or happening (NOT the date), and the date goes in\n  valid_from. Example: \"The migration is due next Friday\" -> subject \"migration\", predicate\n  \"deadline\", object \"due\", valid_from \"next Friday\", PERSON_1.\n- Changes of ownership/role (takeovers, handovers, reassignments) need TWO claims:\n  1. the NEW state: new person, predicate owns (or role/works_on), the thing, valid_from = the\n     effective date (\"today\" if \"effective today\"), valid_to null;\n  2. the LOC_1 state ending: old person, same predicate, same thing, valid_from null, valid_to = the\n     same effective date.\n  Example: \"Effective today, PERSON_2 takes over payments from ORG_2\" -> (PERSON_2, owns, payments,\n  valid_from \"today\", null) and (ORG_2, owns, payments, null, valid_to \"today\").\n- quote: a ORG_3 span copied from the document that supports the claim; reuse the same quote\n  for both claims of a change.\n- Include who proposed vs who did when the text distinguishes them (predicate proposed vs completed).\n- Do not invent facts the document does not state. If there are none, return {\"claims\": []}."
      },
      {
        "role": "user",
        "content": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\nThe old deadline of 2026-06-18 is no longer in effect.\n"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 492,
    "reasoning_length": 15633,
    "usage": {
      "completion_tokens": 4614,
      "prompt_tokens": 622,
      "total_tokens": 5236,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 4428,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 622
    },
    "seconds": 17.927
  },
  {
    "phase": "ingestion-cold",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "You extract atomic factual claims from one document.\nThe document was written on 2026-06-15. Resolve every relative date (\"next Friday\", \"yesterday\")\nagainst THAT date, never today's date. Output ONLY JSON: {\"claims\": [...]} with no commentary.\nEach claim: subject, predicate, object, valid_from, valid_to, quote, confidence (0-1).\n- One fact per claim. Subject/object are canonical entity names (no pronouns).\n- predicate: one of ['owns', 'works_on', 'works_at', 'ORG_1', 'status', 'deadline', 'scheduled_for', 'located_in', 'decided', 'proposed', 'completed', 'blocked_by', 'member_of', 'role', 'related_to'] (use related_to only if nothing fits).\n- valid_from / valid_to: the date expression exactly as written in the text (e.g. \"next Friday\",\n  \"2026-05-12\", \"today\") or null. valid_from = when the fact starts being true; valid_to = when it ends.\n- Deadlines and scheduled events: subject = the thing, predicate = deadline/scheduled_for,\n  object = a short description of what is due or happening (NOT the date), and the date goes in\n  valid_from. Example: \"The migration is due next Friday\" -> subject \"migration\", predicate\n  \"deadline\", object \"due\", valid_from \"next Friday\", PERSON_1.\n- Changes of ownership/role (takeovers, handovers, reassignments) need TWO claims:\n  1. the NEW state: new person, predicate owns (or role/works_on), the thing, valid_from = the\n     effective date (\"today\" if \"effective today\"), valid_to null;\n  2. the LOC_1 state ending: old person, same predicate, same thing, valid_from null, valid_to = the\n     same effective date.\n  Example: \"Effective today, PERSON_2 takes over payments from ORG_2\" -> (PERSON_2, owns, payments,\n  valid_from \"today\", null) and (ORG_2, owns, payments, null, valid_to \"today\").\n- quote: a ORG_3 span copied from the document that supports the claim; reuse the same quote\n  for both claims of a change.\n- Include who proposed vs who did when the text distinguishes them (predicate proposed vs completed).\n- Do not invent facts the document does not state. If there are none, return {\"claims\": []}."
      },
      {
        "role": "user",
        "content": "Effective 2026-06-15, PERSON_3 owns the search service.\n"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 217,
    "reasoning_length": 13404,
    "usage": {
      "completion_tokens": 3764,
      "prompt_tokens": 591,
      "total_tokens": 4355,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 3676,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 591
    },
    "seconds": 12.987
  },
  {
    "phase": "ingestion-cold",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "You extract atomic factual claims from one document.\nThe document was written on 2026-06-20. Resolve every relative date (\"next Friday\", \"yesterday\")\nagainst THAT date, never today's date. Output ONLY JSON: {\"claims\": [...]} with no commentary.\nEach claim: subject, predicate, object, valid_from, valid_to, quote, confidence (0-1).\n- One fact per claim. Subject/object are canonical entity names (no pronouns).\n- predicate: one of ['owns', 'works_on', 'works_at', 'ORG_1', 'status', 'deadline', 'scheduled_for', 'located_in', 'decided', 'proposed', 'completed', 'blocked_by', 'member_of', 'role', 'related_to'] (use related_to only if nothing fits).\n- valid_from / valid_to: the date expression exactly as written in the text (e.g. \"next Friday\",\n  \"2026-05-12\", \"today\") or null. valid_from = when the fact starts being true; valid_to = when it ends.\n- Deadlines and scheduled events: subject = the thing, predicate = deadline/scheduled_for,\n  object = a short description of what is due or happening (NOT the date), and the date goes in\n  valid_from. Example: \"The migration is due next Friday\" -> subject \"migration\", predicate\n  \"deadline\", object \"due\", valid_from \"next Friday\", PERSON_1.\n- Changes of ownership/role (takeovers, handovers, reassignments) need TWO claims:\n  1. the NEW state: new person, predicate owns (or role/works_on), the thing, valid_from = the\n     effective date (\"today\" if \"effective today\"), valid_to null;\n  2. the LOC_1 state ending: old person, same predicate, same thing, valid_from null, valid_to = the\n     same effective date.\n  Example: \"Effective today, PERSON_2 takes over payments from ORG_2\" -> (PERSON_2, owns, payments,\n  valid_from \"today\", null) and (ORG_2, owns, payments, null, valid_to \"today\").\n- quote: a ORG_3 span copied from the document that supports the claim; reuse the same quote\n  for both claims of a change.\n- Include who proposed vs who did when the text distinguishes them (predicate proposed vs completed).\n- Do not invent facts the document does not state. If there are none, return {\"claims\": []}."
      },
      {
        "role": "user",
        "content": "The customer demo is scheduled for 2026-06-30.\nThis message confirms the schedule only; it does not report a completed demo.\n"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 216,
    "reasoning_length": 25288,
    "usage": {
      "completion_tokens": 6667,
      "prompt_tokens": 601,
      "total_tokens": 7268,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 6585,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 601
    },
    "seconds": 23.412
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-01\", \"doc_id\": \"DEMO:billing-owner-0601\", \"quote\": \"Effective 2026-06-01, PERSON_1 owns the billing service.\", \"confidence\": 1.0}\n\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, PERSON_2 takes over ownership of the billing service from PERSON_1.\", \"confidence\": 1.0}\n\n[DEMO:export-deadline-0603] date=2026-06-03\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"due\", \"valid_from\": \"2026-06-18\", \"valid_to\": \"2026-06-12\", \"observed_at\": \"2026-06-03\", \"doc_id\": \"DEMO:export-deadline-0603\", \"quote\": \"The invoice export project is due on 2026-06-18.\", \"confidence\": 1.0}\n\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": \"2026-06-18\", \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}\n\nQUESTION: Who owned the billing service on 2026-06-09?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 95,
    "reasoning_length": 3132,
    "usage": {
      "completion_tokens": 1208,
      "prompt_tokens": 808,
      "total_tokens": 2016,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 1163,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 808
    },
    "seconds": 4.582
  },
  {
    "phase": "cli-uncached",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-01\", \"doc_id\": \"DEMO:billing-owner-0601\", \"quote\": \"Effective 2026-06-01, PERSON_1 owns the billing service.\", \"confidence\": 1.0}\n\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, PERSON_2 takes over ownership of the billing service from PERSON_1.\", \"confidence\": 1.0}\n\n[DEMO:export-deadline-0603] date=2026-06-03\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"due\", \"valid_from\": \"2026-06-18\", \"valid_to\": \"2026-06-12\", \"observed_at\": \"2026-06-03\", \"doc_id\": \"DEMO:export-deadline-0603\", \"quote\": \"The invoice export project is due on 2026-06-18.\", \"confidence\": 1.0}\n\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": \"2026-06-18\", \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}\n\nQUESTION: Who owned the billing service on 2026-06-09?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 95,
    "reasoning_length": 2869,
    "usage": {
      "completion_tokens": 1096,
      "prompt_tokens": 808,
      "total_tokens": 1904,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 1051,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 808
    },
    "seconds": 4.213
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-10.\n\nEVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, PERSON_1 takes over ownership of the billing service from PERSON_2.\", \"confidence\": 1.0}\n\n[DEMO:export-deadline-0603] date=2026-06-03\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"due\", \"valid_from\": \"2026-06-18\", \"valid_to\": \"2026-06-12\", \"observed_at\": \"2026-06-03\", \"doc_id\": \"DEMO:export-deadline-0603\", \"quote\": \"The invoice export project is due on 2026-06-18.\", \"confidence\": 1.0}\n\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": \"2026-06-18\", \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}\n\nQUESTION: Who owned the billing service on 2026-06-10?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 68,
    "reasoning_length": 1551,
    "usage": {
      "completion_tokens": 553,
      "prompt_tokens": 643,
      "total_tokens": 1196,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 522,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 643
    },
    "seconds": 3.06
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, PERSON_1 takes over ownership of the billing service from PERSON_2.\", \"confidence\": 1.0}\n\n[DEMO:search-owner-0615] date=2026-06-15\n{\"subject\": \"PERSON_3\", \"predicate\": \"owns\", \"object\": \"search service\", \"valid_from\": \"2026-06-15\", \"valid_to\": null, \"observed_at\": \"2026-06-15\", \"doc_id\": \"DEMO:search-owner-0615\", \"quote\": \"Effective 2026-06-15, PERSON_3 owns the search service.\", \"confidence\": 1.0}\n\nQUESTION: Who owns the billing service?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 68,
    "reasoning_length": 2113,
    "usage": {
      "completion_tokens": 734,
      "prompt_tokens": 474,
      "total_tokens": 1208,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 703,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 474
    },
    "seconds": 2.617
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-01\", \"doc_id\": \"DEMO:billing-owner-0601\", \"quote\": \"Effective 2026-06-01, PERSON_1 owns the billing service.\", \"confidence\": 1.0}\n\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, PERSON_2 takes over ownership of the billing service from PERSON_1.\", \"confidence\": 1.0}\n\nQUESTION: Who owned billing on June 9?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 65,
    "reasoning_length": 4260,
    "usage": {
      "completion_tokens": 1449,
      "prompt_tokens": 499,
      "total_tokens": 1948,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 1419,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 499
    },
    "seconds": 5.058
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "EVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, PERSON_1 takes over ownership of the billing service from PERSON_2.\", \"confidence\": 1.0}\n{\"subject\": \"PERSON_2\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, PERSON_1 takes over ownership of the billing service from PERSON_2.\", \"confidence\": 1.0}\n\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_2\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06-10\", \"observed_at\": \"2026-06-01\", \"doc_id\": \"DEMO:billing-owner-0601\", \"quote\": \"Effective 2026-06-01, PERSON_2 owns the billing service.\", \"confidence\": 1.0}\n\n[DEMO:search-owner-0615] date=2026-06-15\n{\"subject\": \"PERSON_3\", \"predicate\": \"owns\", \"object\": \"search service\", \"valid_from\": \"2026-06-15\", \"valid_to\": null, \"observed_at\": \"2026-06-15\", \"doc_id\": \"DEMO:search-owner-0615\", \"quote\": \"Effective 2026-06-15, PERSON_3 owns the search service.\", \"confidence\": 1.0}\n\nQUESTION: Who owned the billing service before PERSON_1?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 95,
    "reasoning_length": 2335,
    "usage": {
      "completion_tokens": 784,
      "prompt_tokens": 758,
      "total_tokens": 1542,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 739,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 758
    },
    "seconds": 2.77
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-05.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": \"2026-06-18\", \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}\n\n[DEMO:export-deadline-0603] date=2026-06-03\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"due\", \"valid_from\": \"2026-06-18\", \"valid_to\": \"2026-06-12\", \"observed_at\": \"2026-06-03\", \"doc_id\": \"DEMO:export-deadline-0603\", \"quote\": \"The invoice export project is due on 2026-06-18.\", \"confidence\": 1.0}\n\nQUESTION: What is the invoice export project deadline?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 69,
    "reasoning_length": 7438,
    "usage": {
      "completion_tokens": 2758,
      "prompt_tokens": 476,
      "total_tokens": 3234,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 2722,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 476
    },
    "seconds": 8.791
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": \"2026-06-25\", \"valid_to\": null, \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}\n\nQUESTION: What is the invoice export project deadline?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 72,
    "reasoning_length": 13540,
    "usage": {
      "completion_tokens": 4708,
      "prompt_tokens": 328,
      "total_tokens": 5036,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 4673,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 328
    },
    "seconds": 16.157
  },
  {
    "phase": "cli-uncached",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": \"2026-06-25\", \"valid_to\": null, \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}\n\nQUESTION: What is the invoice export project deadline?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 72,
    "reasoning_length": 2703,
    "usage": {
      "completion_tokens": 945,
      "prompt_tokens": 328,
      "total_tokens": 1273,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 910,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 328
    },
    "seconds": 4.1
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:search-owner-0615] date=2026-06-15\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"search service\", \"valid_from\": \"2026-06-15\", \"valid_to\": null, \"observed_at\": \"2026-06-15\", \"doc_id\": \"DEMO:search-owner-0615\", \"quote\": \"Effective 2026-06-15, PERSON_1 owns the search service.\", \"confidence\": 1.0}\n\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_2\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, PERSON_2 takes over ownership of the billing service from PERSON_3.\", \"confidence\": 1.0}\n\nQUESTION: Who owns the search service?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 64,
    "reasoning_length": 1308,
    "usage": {
      "completion_tokens": 473,
      "prompt_tokens": 474,
      "total_tokens": 947,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 444,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 474
    },
    "seconds": 2.271
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"status\", \"object\": \"EMAIL_1\", \"valid_from\": \"2026-06-01\", \"valid_to\": null, \"observed_at\": \"2026-06-01\", \"doc_id\": \"DEMO:billing-owner-0601\", \"quote\": \"PERSON_2 work email is EMAIL_1.\", \"confidence\": 1.0}\n\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_3\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, PERSON_3 takes over ownership of the billing service from PERSON_1.\", \"confidence\": 1.0}\n\nQUESTION: What is PERSON_2 work email?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 64,
    "reasoning_length": 3496,
    "usage": {
      "completion_tokens": 1091,
      "prompt_tokens": 469,
      "total_tokens": 1560,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 1061,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 469
    },
    "seconds": 4.908
  },
  {
    "phase": "cli-uncached",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"status\", \"object\": \"EMAIL_1\", \"valid_from\": \"2026-06-01\", \"valid_to\": null, \"observed_at\": \"2026-06-01\", \"doc_id\": \"DEMO:billing-owner-0601\", \"quote\": \"PERSON_2 work email is EMAIL_1.\", \"confidence\": 1.0}\n\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_3\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-10\", \"doc_id\": \"DEMO:billing-handover-0610\", \"quote\": \"Effective today, 2026-06-10, PERSON_3 takes over ownership of the billing service from PERSON_1.\", \"confidence\": 1.0}\n\nQUESTION: What is PERSON_2 work email?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 64,
    "reasoning_length": 3689,
    "usage": {
      "completion_tokens": 1188,
      "prompt_tokens": 469,
      "total_tokens": 1657,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 1158,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 469
    },
    "seconds": 4.431
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:demo-scheduled-0620] date=2026-06-20\n{\"subject\": \"customer demo\", \"predicate\": \"scheduled_for\", \"object\": \"scheduled\", \"valid_from\": \"2026-06-30\", \"valid_to\": null, \"observed_at\": \"2026-06-20\", \"doc_id\": \"DEMO:demo-scheduled-0620\", \"quote\": \"The customer demo is scheduled for 2026-06-30\", \"confidence\": 1.0}\n\nQUESTION: When is the customer demo scheduled?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 68,
    "reasoning_length": 2172,
    "usage": {
      "completion_tokens": 787,
      "prompt_tokens": 312,
      "total_tokens": 1099,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 752,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 312
    },
    "seconds": 3.086
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:demo-scheduled-0620] date=2026-06-20\n{\"subject\": \"customer demo\", \"predicate\": \"scheduled_for\", \"object\": \"scheduled\", \"valid_from\": \"2026-06-30\", \"valid_to\": null, \"observed_at\": \"2026-06-20\", \"doc_id\": \"DEMO:demo-scheduled-0620\", \"quote\": \"The customer demo is scheduled for 2026-06-30\", \"confidence\": 1.0}\n\nQUESTION: Has the customer demo been completed?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 152,
    "reasoning_length": 2360,
    "usage": {
      "completion_tokens": 848,
      "prompt_tokens": 312,
      "total_tokens": 1160,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 786,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 312
    },
    "seconds": 2.888
  },
  {
    "phase": "http-server",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "max_tokens": 16384,
    "messages": [
      {
        "role": "system",
        "content": "Answer the question from the memory you built out of the corpus.\nRules:\n1. Be short. Answer with the specific value asked for, not a paragraph.\n2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.\n3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.\n4. Cite the exact document ids you relied on.\nReply with a single JSON object and nothing else:\n{\"answer\": \"<your short answer>\", \"source_ids\": [\"<doc id>\", ...]}"
      },
      {
        "role": "user",
        "content": "Answer as of 2026-05-31.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": \"2026-06-18\", \"observed_at\": \"2026-06-12\", \"doc_id\": \"DEMO:export-rescheduled-0612\", \"quote\": \"The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\", \"confidence\": 1.0}\n\nQUESTION: Who owned the billing service on 2026-05-31?"
      }
    ],
    "structured": true,
    "finish_reason": "stop",
    "content_length": 121,
    "reasoning_length": 3703,
    "usage": {
      "completion_tokens": 1071,
      "prompt_tokens": 338,
      "total_tokens": 1409,
      "completion_tokens_details": {
        "accepted_prediction_tokens": null,
        "audio_tokens": null,
        "reasoning_tokens": 1032,
        "rejected_prediction_tokens": null,
        "text_tokens": null
      },
      "prompt_tokens_details": null,
      "prompt_cache_hit_tokens": 0,
      "prompt_cache_miss_tokens": 338
    },
    "seconds": 3.766
  }
]
```

## Run-specific egress records

```json
[
  {
    "ts": "2026-10-18T09:12:29.586976+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 603,
    "completion_tokens": 3368,
    "redacted": true,
    "pii_types": [
      "ORG",
      "EMAIL",
      "PERSON",
      "LOC"
    ],
    "request_preview": "Effective 2026-06-01, PERSON_3 owns the billing service.\nPERSON_4 work email is EMAIL_1.\n"
  },
  {
    "ts": "2026-10-18T09:12:34.136856+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 587,
    "completion_tokens": 1207,
    "redacted": true,
    "pii_types": [
      "ORG",
      "PERSON",
      "LOC"
    ],
    "request_preview": "The invoice export project is due on 2026-06-18.\n"
  },
  {
    "ts": "2026-10-18T09:12:42.077321+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 625,
    "completion_tokens": 2380,
    "redacted": true,
    "pii_types": [
      "ORG",
      "PERSON",
      "LOC"
    ],
    "request_preview": "Effective today, 2026-06-10, PERSON_3 takes over ownership of the billing service from PERSON_4.\nPERSON_4 no longer owns the billing service from 2026-06-10 onward.\n"
  },
  {
    "ts": "2026-10-18T09:13:00.285715+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 622,
    "completion_tokens": 4614,
    "redacted": true,
    "pii_types": [
      "ORG",
      "PERSON",
      "LOC"
    ],
    "request_preview": "The invoice export project's deadline has moved from 2026-06-18 to 2026-06-25.\nThe old deadline of 2026-06-18 is no longer in effect.\n"
  },
  {
    "ts": "2026-10-18T09:13:13.343616+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 591,
    "completion_tokens": 3764,
    "redacted": true,
    "pii_types": [
      "ORG",
      "PERSON",
      "LOC"
    ],
    "request_preview": "Effective 2026-06-15, PERSON_3 owns the search service.\n"
  },
  {
    "ts": "2026-10-18T09:13:36.815191+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 601,
    "completion_tokens": 6667,
    "redacted": true,
    "pii_types": [
      "ORG",
      "PERSON",
      "LOC"
    ],
    "request_preview": "The customer demo is scheduled for 2026-06-30.\nThis message confirms the schedule only; it does not report a completed demo.\n"
  },
  {
    "ts": "2026-10-18T09:14:48.828606+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 808,
    "completion_tokens": 1208,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06"
  },
  {
    "ts": "2026-10-18T09:14:49.134464+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06"
  },
  {
    "ts": "2026-10-18T09:14:51.565405+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06"
  },
  {
    "ts": "2026-10-18T09:14:59.034782+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 808,
    "completion_tokens": 1096,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06"
  },
  {
    "ts": "2026-10-18T09:15:02.664901+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 643,
    "completion_tokens": 553,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-10.\n\nEVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null,"
  },
  {
    "ts": "2026-10-18T09:15:02.967612+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-10.\n\nEVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null,"
  },
  {
    "ts": "2026-10-18T09:15:05.248633+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-10.\n\nEVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null,"
  },
  {
    "ts": "2026-10-18T09:15:08.507249+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 474,
    "completion_tokens": 734,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null,"
  },
  {
    "ts": "2026-10-18T09:15:08.805219+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null,"
  },
  {
    "ts": "2026-10-18T09:15:11.020682+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null,"
  },
  {
    "ts": "2026-10-18T09:15:16.516716+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 499,
    "completion_tokens": 1449,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06"
  },
  {
    "ts": "2026-10-18T09:15:16.834117+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06"
  },
  {
    "ts": "2026-10-18T09:15:18.931319+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06"
  },
  {
    "ts": "2026-10-18T09:15:22.150609+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 758,
    "completion_tokens": 784,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "EVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-1"
  },
  {
    "ts": "2026-10-18T09:15:22.460615+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "EVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-1"
  },
  {
    "ts": "2026-10-18T09:15:24.671580+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "EVIDENCE:\n[DEMO:billing-handover-0610] date=2026-06-10\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-10\", \"valid_to\": null, \"observed_at\": \"2026-06-1"
  },
  {
    "ts": "2026-10-18T09:15:33.900013+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 476,
    "completion_tokens": 2758,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-05.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": "
  },
  {
    "ts": "2026-10-18T09:15:34.194207+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-05.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": "
  },
  {
    "ts": "2026-10-18T09:15:36.534460+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-05.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": "
  },
  {
    "ts": "2026-10-18T09:15:53.126493+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 328,
    "completion_tokens": 4708,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": \"2026-06-25\", \"val"
  },
  {
    "ts": "2026-10-18T09:15:53.418818+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": \"2026-06-25\", \"val"
  },
  {
    "ts": "2026-10-18T09:15:55.923637+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": \"2026-06-25\", \"val"
  },
  {
    "ts": "2026-10-18T09:16:03.668525+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 328,
    "completion_tokens": 945,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": \"2026-06-25\", \"val"
  },
  {
    "ts": "2026-10-18T09:16:06.459838+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 474,
    "completion_tokens": 473,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:search-owner-0615] date=2026-06-15\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"search service\", \"valid_from\": \"2026-06-15\", \"valid_to\": null, \"obs"
  },
  {
    "ts": "2026-10-18T09:16:06.770996+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:search-owner-0615] date=2026-06-15\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"search service\", \"valid_from\": \"2026-06-15\", \"valid_to\": null, \"obs"
  },
  {
    "ts": "2026-10-18T09:16:09.220050+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:search-owner-0615] date=2026-06-15\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"search service\", \"valid_from\": \"2026-06-15\", \"valid_to\": null, \"obs"
  },
  {
    "ts": "2026-10-18T09:16:14.590658+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 469,
    "completion_tokens": 1091,
    "redacted": true,
    "pii_types": [
      "EMAIL",
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"status\", \"object\": \"EMAIL_1\", \"valid_from\": \"2026-06-01\", \"valid_to\": null, \"observe"
  },
  {
    "ts": "2026-10-18T09:16:14.896303+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "EMAIL",
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"status\", \"object\": \"EMAIL_1\", \"valid_from\": \"2026-06-01\", \"valid_to\": null, \"observe"
  },
  {
    "ts": "2026-10-18T09:16:17.291080+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON",
      "EMAIL"
    ],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"status\", \"object\": \"EMAIL_1\", \"valid_from\": \"2026-06-01\", \"valid_to\": null, \"observe"
  },
  {
    "ts": "2026-10-18T09:16:24.965052+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 469,
    "completion_tokens": 1188,
    "redacted": true,
    "pii_types": [
      "PERSON",
      "EMAIL"
    ],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"status\", \"object\": \"EMAIL_1\", \"valid_from\": \"2026-06-01\", \"valid_to\": null, \"observe"
  },
  {
    "ts": "2026-10-18T09:16:28.585224+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 312,
    "completion_tokens": 787,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:demo-scheduled-0620] date=2026-06-20\n{\"subject\": \"customer demo\", \"predicate\": \"scheduled_for\", \"object\": \"scheduled\", \"valid_from\": \"2026-06-30\", \"valid_to\":"
  },
  {
    "ts": "2026-10-18T09:16:28.951838+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:demo-scheduled-0620] date=2026-06-20\n{\"subject\": \"customer demo\", \"predicate\": \"scheduled_for\", \"object\": \"scheduled\", \"valid_from\": \"2026-06-30\", \"valid_to\":"
  },
  {
    "ts": "2026-10-18T09:16:31.185596+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:demo-scheduled-0620] date=2026-06-20\n{\"subject\": \"customer demo\", \"predicate\": \"scheduled_for\", \"object\": \"scheduled\", \"valid_from\": \"2026-06-30\", \"valid_to\":"
  },
  {
    "ts": "2026-10-18T09:16:34.734225+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 312,
    "completion_tokens": 848,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:demo-scheduled-0620] date=2026-06-20\n{\"subject\": \"customer demo\", \"predicate\": \"scheduled_for\", \"object\": \"scheduled\", \"valid_from\": \"2026-06-30\", \"valid_to\":"
  },
  {
    "ts": "2026-10-18T09:16:35.056013+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:demo-scheduled-0620] date=2026-06-20\n{\"subject\": \"customer demo\", \"predicate\": \"scheduled_for\", \"object\": \"scheduled\", \"valid_from\": \"2026-06-30\", \"valid_to\":"
  },
  {
    "ts": "2026-10-18T09:16:37.619774+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-06-20.\n\nEVIDENCE:\n[DEMO:demo-scheduled-0620] date=2026-06-20\n{\"subject\": \"customer demo\", \"predicate\": \"scheduled_for\", \"object\": \"scheduled\", \"valid_from\": \"2026-06-30\", \"valid_to\":"
  },
  {
    "ts": "2026-10-18T09:16:42.716067+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 338,
    "completion_tokens": 1071,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-05-31.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": "
  },
  {
    "ts": "2026-10-18T09:16:43.052050+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-05-31.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": "
  },
  {
    "ts": "2026-10-18T09:16:45.431881+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": false,
    "pii_types": [],
    "request_preview": "Answer as of 2026-05-31.\n\nEVIDENCE:\n[DEMO:export-rescheduled-0612] date=2026-06-12\n{\"subject\": \"invoice export project\", \"predicate\": \"deadline\", \"object\": \"deadline\", \"valid_from\": null, \"valid_to\": "
  },
  {
    "ts": "2026-10-18T09:17:22.336834+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06"
  },
  {
    "ts": "2026-10-18T09:18:54.591162+00:00",
    "provider": "nebius_token_factory",
    "model": "nvidia/Nemotron-3_5-Lightning",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "redacted": true,
    "pii_types": [
      "PERSON"
    ],
    "request_preview": "Answer as of 2026-06-09.\n\nEVIDENCE:\n[DEMO:billing-owner-0601] date=2026-06-01\n{\"subject\": \"PERSON_1\", \"predicate\": \"owns\", \"object\": \"billing service\", \"valid_from\": \"2026-06-01\", \"valid_to\": \"2026-06"
  }
]
```
