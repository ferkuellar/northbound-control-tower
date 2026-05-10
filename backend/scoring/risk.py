from findings.rules import FindingType


FINDING_RISK_WEIGHTS: dict[FindingType, int] = {
    FindingType.IDLE_COMPUTE: 15,
    FindingType.PUBLIC_EXPOSURE: 30,
    FindingType.MISSING_TAGS: 10,
    FindingType.UNATTACHED_VOLUMES: 15,
    FindingType.OBSERVABILITY_GAPS: 20,
}


def cap_risk_score(score: int) -> int:
    return max(0, min(score, 100))
