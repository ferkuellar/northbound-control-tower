from scoring.enums import ScoreType

FORMULA_VERSION = "phase7.v1"

SEVERITY_DEDUCTIONS = {
    "critical": 25,
    "high": 15,
    "medium": 8,
    "low": 3,
    "informational": 1,
}

OVERALL_WEIGHTS = {
    ScoreType.FINOPS.value: 0.20,
    ScoreType.GOVERNANCE.value: 0.20,
    ScoreType.OBSERVABILITY.value: 0.20,
    ScoreType.SECURITY_BASELINE.value: 0.25,
    ScoreType.RESILIENCE.value: 0.15,
}

SCORE_TYPE_FINDING_MAP = {
    ScoreType.FINOPS.value: {"idle_compute", "unattached_volume"},
    ScoreType.GOVERNANCE.value: {"missing_tags"},
    ScoreType.OBSERVABILITY.value: {"observability_gap"},
    ScoreType.SECURITY_BASELINE.value: {"public_exposure"},
    ScoreType.RESILIENCE.value: {"observability_gap"},
}

SCORE_TYPE_DEDUCTION_MULTIPLIERS = {
    ScoreType.RESILIENCE.value: 0.5,
}
