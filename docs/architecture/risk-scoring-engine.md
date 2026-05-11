# Risk Scoring Engine

## Purpose

The Risk Scoring Engine converts deterministic findings into explainable operational scores for cloud management. It uses normalized resources and findings from previous phases and persists score history for trends and future dashboard/reporting use.

## Scoring Philosophy

Scores are:
- Deterministic
- Explainable
- Auditable
- Tenant-scoped
- Independent from AI

AI may later explain or summarize scores, but it must not calculate them.

## Deterministic Scoring Rules

Each score starts at 100. Active findings deduct points based on severity.

Included finding statuses:
- `open`
- `acknowledged`

Excluded finding statuses:
- `resolved`
- `false_positive`

Scores are clamped between 0 and 100.

## Severity Deduction Model

Default deductions:
- `critical`: 25
- `high`: 15
- `medium`: 8
- `low`: 3
- `informational`: 1

## Score Types

### FinOps

Finding types:
- `idle_compute`
- `unattached_volume`

### Governance

Finding types:
- `missing_tags`

### Observability

Finding types:
- `observability_gap`

### Security Baseline

Finding types:
- `public_exposure`

### Resilience

Finding types:
- `observability_gap`

Resilience applies a lighter deduction multiplier because observability affects resilience but should not dominate it in Phase 7.

### Overall Cloud Operational Score

Weighted average:
- `finops`: 0.20
- `governance`: 0.20
- `observability`: 0.20
- `security_baseline`: 0.25
- `resilience`: 0.15

## Grade Mapping

- 90-100: `excellent`
- 75-89: `good`
- 60-74: `fair`
- 40-59: `poor`
- 0-39: `critical`

## Trend Model

The engine compares the latest score with the previous score for the same:
- tenant
- cloud account scope
- provider scope
- score type

Trend:
- `improving`: score increased by 3 or more.
- `degrading`: score decreased by 3 or more.
- `stable`: change is between -2 and +2.
- `unknown`: no previous score exists.

## Evidence

Each persisted score includes JSON evidence:
- total resources
- total findings
- findings by severity
- findings by type
- formula version
- weights used
- deductions
- provider
- cloud account id
- top drivers

Evidence must not contain secrets or raw cloud credential material.

## Known Limitations

- Scores depend on finding quality and normalized metadata coverage.
- No AI-generated scoring.
- No report generation.
- No dashboard.
- No configurable tenant-specific weights yet.
- No risk acceptance workflow yet.

## Future Improvements

- Tenant-specific scoring weights.
- Risk acceptance and exception policies.
- Time-windowed score deltas.
- Score comparison by account/provider/business unit.
- Dashboard and executive reports.
- AI explanations that consume score evidence without changing score values.
