from enum import StrEnum


class ScoreType(StrEnum):
    FINOPS = "finops"
    GOVERNANCE = "governance"
    OBSERVABILITY = "observability"
    SECURITY_BASELINE = "security_baseline"
    RESILIENCE = "resilience"
    OVERALL = "overall"


class ScoreGrade(StrEnum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class ScoreTrend(StrEnum):
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    UNKNOWN = "unknown"
