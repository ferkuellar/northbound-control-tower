from scoring.formulas import calculate_score, calculate_weighted_overall, grade_for_score, severity_deduction, trend_for_scores
from scoring.enums import ScoreGrade, ScoreTrend


class _Finding:
    def __init__(self, severity: str) -> None:
        self.severity = severity


def test_severity_deductions() -> None:
    assert severity_deduction("critical") == 25
    assert severity_deduction("high") == 15
    assert severity_deduction("medium") == 8
    assert severity_deduction("low") == 3
    assert severity_deduction("informational") == 1


def test_score_clamps_between_zero_and_hundred() -> None:
    findings = [_Finding("critical") for _ in range(10)]

    assert calculate_score(findings) == 0
    assert calculate_score([]) == 100


def test_grade_mapping() -> None:
    assert grade_for_score(95) == ScoreGrade.EXCELLENT
    assert grade_for_score(80) == ScoreGrade.GOOD
    assert grade_for_score(65) == ScoreGrade.FAIR
    assert grade_for_score(50) == ScoreGrade.POOR
    assert grade_for_score(20) == ScoreGrade.CRITICAL


def test_weighted_overall_score() -> None:
    score = calculate_weighted_overall(
        {
            "finops": 100,
            "governance": 80,
            "observability": 60,
            "security_baseline": 40,
            "resilience": 100,
        }
    )

    assert score == 73


def test_trend_calculation() -> None:
    assert trend_for_scores(90, None) == ScoreTrend.UNKNOWN
    assert trend_for_scores(90, 85) == ScoreTrend.IMPROVING
    assert trend_for_scores(80, 85) == ScoreTrend.DEGRADING
    assert trend_for_scores(84, 85) == ScoreTrend.STABLE
