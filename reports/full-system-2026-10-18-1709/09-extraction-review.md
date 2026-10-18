# Extraction review and stored-data concerns

The live run extracted 9 claims from 6 synthetic documents; no document failed and the extractor dropped no claims. This is ingestion success, not 100% extraction accuracy. The complete claims are preserved in [the ingestion report](06-ingestion.md).

| Claim | Assessment |
|---|---|
| Maya owns billing from June 1 | Supported; correct start date |
| Maya's email | Value and quote are correct, but predicate is `status`, which misclassifies an email as an entity status |
| Original invoice export deadline June 18 | Supported; P2 stores the due date in `event_at` |
| Noah owns billing from June 10 | Supported |
| Maya's ownership closes June 10 | Supported; merged into the existing ownership fact |
| Revised invoice export deadline June 25 | Supported |
| Extra closing deadline claim with unknown start and `valid_to=June 18` | Problematic representation: the old deadline ceased being in force on June 12, not June 18. The model also used object `deadline` rather than the original `due`, so P2 retained a separate closing-only fact |
| Iris owns search from June 15 | Supported |
| Demo scheduled June 30 | Supported; does not establish completion |

Seven of nine extracted records have no issue identified in this review. The email record has a semantic classification issue; the extra deadline closure has inconsistent temporal/slot representation. This is a manual review of these records, not a general extraction-accuracy estimate. All nine quotes are grounded in the synthetic source texts, but a verbatim quote alone does not validate the extracted predicate or interval.

P2 correctly closes the original active deadline on June 12 and opens the new deadline that day. However, it also retains the extra closing-only deadline record with unknown start. That record can appear in dates before the corpus began, because unknown start means no known lower bound. The `before-corpus` question retrieved this unrelated deadline record: search matched date tokens such as `2026`. The answerer correctly abstained, but it made an unnecessary provider call.

Recommended follow-up (not applied during this run): distinguish contact attributes from status; normalize deadline slots; prevent deadline replacement from generating a second contradictory closing-only event; strip question date tokens from lexical retrieval while retaining them as temporal filters. Keep source-dated provenance and do not substitute transaction-time filtering for valid-time semantics.
