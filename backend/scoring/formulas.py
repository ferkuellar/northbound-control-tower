from __future__ import annotations

from collections.abc import Iterable

from models.finding import Finding
from scoring.enums import ScoreGrade, ScoreTrend
from scoring.weights import OVERALL_WEIGHTS, SEVERITY_DEDUCTIONS


def clamp_score(value: float) -> int:
    return max(0, min(100, round(value)))


def severity_deduction(severity: str, *, multiplier: float = 1.0) -> float:
    return SEVERITY_DEDUCTIONS.get(severity, 0) * multiplier


def calculate_score(findings: Iterable[Finding], *, multiplier: float = 1.0) -> int:
    total_deduction = sum(severity_deduction(finding.severity, multiplier=multiplier) for finding in findings)
    return clamp_score(100 - total_deduction)


def calculate_weighted_overall(domain_scores: dict[str, int]) -> int:
    weighted = sum(domain_scores[key] * weight for key, weight in OVERALL_WEIGHTS.items())
    return clamp_score(weighted)


def grade_for_score(score: int) -> ScoreGrade:
    if score >= 90:
        return ScoreGrade.EXCELLENT
    if score >= 75:
        return ScoreGrade.GOOD
    if score >= 60:
        return ScoreGrade.FAIR
    if score >= 40:
        return ScoreGrade.POOR
    return ScoreGrade.CRITICAL


def trend_for_scores(current_score: int, previous_score: int | None) -> ScoreTrend:
    if previous_score is None:
        return ScoreTrend.UNKNOWN
    delta = current_score - previous_score
    if delta >= 3:
        return ScoreTrend.IMPROVING
    if delta <= -3:
        return ScoreTrend.DEGRADING
    return ScoreTrend.STABLE
