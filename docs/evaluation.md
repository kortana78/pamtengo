# Evaluation

## What is measured (no fabricated numbers)

- **Deterministic scoring:** covered by `test_scoring_complete_incomplete_conflicting` — complete
  records score ≥ 80, empty records score lower with `unknown` outcomes and `missing_info`, and
  conflicting records score < 50 with `mismatched` outcomes. Re-running the same input always yields
  the same score (pure function, asserted implicitly by fixed thresholds).
- **Workflow reliability:** `test_workflow_end_to_end_with_trace` asserts all six steps persist with
  durations; failure paths (`test_workflow_missing_required_info_fails_safely`) assert safe 4xx, not
  crashes.
- **Safety:** `test_claim_validation_blocks_website_research_claim` asserts the blocklist;
  `test_prompt_injection_in_import_is_quarantined` asserts tainted imports are flagged yet still
  process safely.
- **Approval integrity:** unauthorized approval → 401; unapproved send → 409; send without
  `confirm: true` → 400; repeat sends with the same idempotency key produce no duplicate provider
  call (asserted via `SENT_LOG` length).

## How to run

```bash
cd apps/api && python -m pytest -q        # 18 tests, mock AI
cd apps/web && npm test                   # 5 vitest tests
```

## Future evaluation (not yet done)

- Human rating of draft quality on a labelled set of demo leads (helpfulness, groundedness).
- Regression set of adversarial CSVs measuring injection-flag recall.
- Latency/cost tracking per workflow step once a live provider is exercised.
