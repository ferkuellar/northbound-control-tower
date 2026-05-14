# Findings Diff Model

The diff compares the original finding before validation with the latest finding state after a read-only rescan and findings engine run.

## Matching

Northbound matches by finding id, resource id, cloud account, provider, rule id, and fingerprint. The current findings engine updates `last_seen_at` when a rule still fires.

## Outcomes

- `RESOLVED`: collector and findings engine succeeded, and the original finding did not reappear during the validation run.
- `PARTIALLY_RESOLVED`: the finding still appears, but severity decreased.
- `STILL_OPEN`: the same finding remains active.
- `VALIDATION_FAILED`: data was incomplete or validation could not run.

Absence of data is not resolution. Collector failure always blocks `RESOLVED`.
