# Risk Summary Model

## Inputs

The risk summary combines:

- Terraform `plan.json`
- Checkov evidence
- Infracost evidence
- provisioning request metadata
- template risk
- approval requirement

## JSON Structure

`risk-summary.json` includes request identity, template key, provider, environment, finding ID, Terraform plan summary, security summary, cost summary, template risk, approval requirement, and recommendation.

## Markdown Structure

`risk-summary.md` is human-readable and contains:

- Request
- Terraform Plan
- Security
- Cost
- Gate Decision
- Recommendation

## Future Approval

The summary is designed to become the review packet for Phase E approval workflows.

## Executive Reporting

The same structure can feed future portfolio reporting by exposing security posture, cost impact, and gate decision per request.
