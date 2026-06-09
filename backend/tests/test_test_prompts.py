"""Tests for scripts/test_prompts.py — check_executive_summary evaluator and CLI."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.test_prompts import (
    _TOTAL_CRITERIA,
    check_executive_summary,
    evaluate,
    main,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────

def _valid_output() -> dict:
    return {
        "executive_summary": {
            "overall_posture": {
                "risk_level": "high",
                "one_line": (
                    "The environment has material operational risk that should be "
                    "addressed before expanding production usage."
                ),
                "score_context": "An overall score of 49 indicates weak control maturity.",
            },
            "business_risk": {
                "summary": (
                    "The current posture suggests that critical production assets may be "
                    "exposed or poorly governed. If left unresolved, the organization could "
                    "face service disruption, audit findings, and avoidable remediation cost."
                ),
                "top_risks": [
                    {
                        "risk": "Public exposure of production compute",
                        "affected_assets": 1,
                        "impact": "Increases likelihood of unauthorized access attempts.",
                        "urgency": "immediate",
                    }
                ],
            },
            "domain_highlights": [
                {
                    "domain": "security_baseline",
                    "score": 42,
                    "grade": "D",
                    "headline": "Security controls are below an acceptable production baseline.",
                    "top_finding": "EC2 instance publicly accessible without WAF",
                }
            ],
            "recommendations_30_60_90": {
                "days_30": [
                    {
                        "action": (
                            "Restrict public exposure on the affected production compute "
                            "resource after approval, backup, snapshot, and rollback validation."
                        ),
                        "owner": "Security team",
                        "effort": "days",
                        "risk_if_skipped": (
                            "The resource remains exposed and may trigger incident response "
                            "or audit escalation."
                        ),
                    }
                ],
                "days_60": [],
                "days_90": [],
            },
            "limitations": [],
        }
    }


# ── Criterion count is always stable ───────────────────────────────────────────

def test_valid_output_returns_13_criteria() -> None:
    results = check_executive_summary(_valid_output())
    assert len(results) == _TOTAL_CRITERIA


def test_empty_output_returns_13_criteria() -> None:
    results = check_executive_summary({})
    assert len(results) == _TOTAL_CRITERIA


def test_missing_domain_highlights_still_returns_13_criteria() -> None:
    output = _valid_output()
    del output["executive_summary"]["domain_highlights"]
    results = check_executive_summary(output)
    assert len(results) == _TOTAL_CRITERIA


def test_missing_days_30_still_returns_13_criteria() -> None:
    output = _valid_output()
    output["executive_summary"]["recommendations_30_60_90"]["days_30"] = []
    results = check_executive_summary(output)
    assert len(results) == _TOTAL_CRITERIA


# ── Valid output passes all 13 ──────────────────────────────────────────────────

def test_valid_output_passes_all_criteria() -> None:
    results = check_executive_summary(_valid_output())
    failed = [(c, d) for c, ok, d in results if not ok]
    assert failed == [], f"Expected 13/13 but failed: {failed}"


# ── Individual criterion failures ───────────────────────────────────────────────

def test_jargon_in_one_line_fails_criterion() -> None:
    output = _valid_output()
    output["executive_summary"]["overall_posture"]["one_line"] = (
        "The ec2 instance has a critical misconfiguration that must be resolved."
    )
    results = check_executive_summary(output)
    criterion = {c: (ok, d) for c, ok, d in results}
    ok, detail = criterion["one_line without technical jargon"]
    assert not ok
    assert "ec2" in detail


def test_missing_risk_if_skipped_fails_criterion() -> None:
    output = _valid_output()
    output["executive_summary"]["recommendations_30_60_90"]["days_30"][0].pop("risk_if_skipped")
    results = check_executive_summary(output)
    criterion = {c: ok for c, ok, _ in results}
    assert not criterion["has risk_if_skipped"]


def test_invalid_risk_level_fails_criterion() -> None:
    output = _valid_output()
    output["executive_summary"]["overall_posture"]["risk_level"] = "severe"
    results = check_executive_summary(output)
    criterion = {c: ok for c, ok, _ in results}
    assert not criterion["valid risk_level"]


def test_short_one_line_fails_criterion() -> None:
    output = _valid_output()
    output["executive_summary"]["overall_posture"]["one_line"] = "Too short."
    results = check_executive_summary(output)
    criterion = {c: ok for c, ok, _ in results}
    assert not criterion["one_line > 30 chars"]


def test_short_summary_fails_criterion() -> None:
    output = _valid_output()
    output["executive_summary"]["business_risk"]["summary"] = "Short."
    results = check_executive_summary(output)
    criterion = {c: ok for c, ok, _ in results}
    assert not criterion["business_risk.summary > 80 chars"]


def test_empty_top_risks_fails_criterion() -> None:
    output = _valid_output()
    output["executive_summary"]["business_risk"]["top_risks"] = []
    results = check_executive_summary(output)
    criterion = {c: ok for c, ok, _ in results}
    assert not criterion["top_risks not empty"]


def test_empty_domain_highlights_fails_three_criteria() -> None:
    output = _valid_output()
    output["executive_summary"]["domain_highlights"] = []
    results = check_executive_summary(output)
    criterion = {c: ok for c, ok, _ in results}
    assert not criterion["domain_highlights not empty"]
    assert not criterion["domain.score numeric"]
    assert not criterion["domain.headline > 20 chars"]


def test_non_numeric_domain_score_fails_criterion() -> None:
    output = _valid_output()
    output["executive_summary"]["domain_highlights"][0]["score"] = "42"
    results = check_executive_summary(output)
    criterion = {c: ok for c, ok, _ in results}
    assert not criterion["domain.score numeric"]


def test_short_domain_headline_fails_criterion() -> None:
    output = _valid_output()
    output["executive_summary"]["domain_highlights"][0]["headline"] = "Too short."
    results = check_executive_summary(output)
    criterion = {c: ok for c, ok, _ in results}
    assert not criterion["domain.headline > 20 chars"]


# ── Incomplete output: absent days_30 fails criterion (not skips) ───────────────

def test_absent_days_30_fails_risk_if_skipped_criterion() -> None:
    output = _valid_output()
    output["executive_summary"]["recommendations_30_60_90"]["days_30"] = []
    results = check_executive_summary(output)
    criterion = {c: ok for c, ok, _ in results}
    assert not criterion["has risk_if_skipped"]


# ── evaluate() dispatcher ───────────────────────────────────────────────────────

def test_evaluate_returns_results_list() -> None:
    results = evaluate("executive_summary", _valid_output())
    assert isinstance(results, list)
    assert len(results) == _TOTAL_CRITERIA


def test_evaluate_unsupported_type_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported analysis type"):
        evaluate("unknown_type", {})


# ── CLI: --file ─────────────────────────────────────────────────────────────────

def test_cli_file_valid_output_exits_zero() -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(_valid_output(), f)
        tmp_path = f.name

    exit_code = main(["--type", "executive_summary", "--file", tmp_path])
    assert exit_code == 0

    Path(tmp_path).unlink(missing_ok=True)


def test_cli_file_not_found_exits_nonzero() -> None:
    exit_code = main(["--type", "executive_summary", "--file", "/nonexistent/path.json"])
    assert exit_code != 0


def test_cli_invalid_json_exits_nonzero() -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        f.write("not valid json {{{")
        tmp_path = f.name

    exit_code = main(["--type", "executive_summary", "--file", tmp_path])
    assert exit_code != 0

    Path(tmp_path).unlink(missing_ok=True)


def test_cli_no_file_exits_nonzero() -> None:
    exit_code = main(["--type", "executive_summary"])
    assert exit_code != 0


# ── CLI: --strict ───────────────────────────────────────────────────────────────

def test_cli_strict_passes_on_valid_output() -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(_valid_output(), f)
        tmp_path = f.name

    exit_code = main(["--type", "executive_summary", "--file", tmp_path, "--strict"])
    assert exit_code == 0

    Path(tmp_path).unlink(missing_ok=True)


def test_cli_strict_fails_on_invalid_output() -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump({}, f)
        tmp_path = f.name

    exit_code = main(["--type", "executive_summary", "--file", tmp_path, "--strict"])
    assert exit_code == 1

    Path(tmp_path).unlink(missing_ok=True)


def test_cli_no_strict_exits_zero_on_invalid_output() -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump({}, f)
        tmp_path = f.name

    exit_code = main(["--type", "executive_summary", "--file", tmp_path])
    assert exit_code == 0

    Path(tmp_path).unlink(missing_ok=True)
