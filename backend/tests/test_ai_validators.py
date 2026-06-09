from __future__ import annotations

import pytest

from ai.errors import AIOutputValidationError
from ai.validators import LIMITATION_SIGNALS, validate_ai_output

# Context helpers

_CTX_NO_RESOURCES = {"limitations": {"resources_available": False}}
_CTX_WITH_RESOURCES = {"limitations": {"resources_available": True}}


def _output(summary: str) -> str:
    return f'{{"executive_summary": {{"summary": "{summary}"}}}}'


# ── limitation signals — valid ─────────────────────────────────────────────────

def test_accepts_literal_limitation() -> None:
    validate_ai_output(_output("limitation: no resource data"), context=_CTX_NO_RESOURCES)


def test_accepts_constraint() -> None:
    validate_ai_output(_output("constraint: data is unavailable"), context=_CTX_NO_RESOURCES)


def test_accepts_no_data() -> None:
    validate_ai_output(_output("No data available for this analysis."), context=_CTX_NO_RESOURCES)


def test_accepts_unavailable() -> None:
    validate_ai_output(_output("Resource inventory is unavailable."), context=_CTX_NO_RESOURCES)


def test_accepts_not_available() -> None:
    validate_ai_output(_output("Metrics are not available in this context."), context=_CTX_NO_RESOURCES)


def test_accepts_missing_data() -> None:
    validate_ai_output(_output("missing data prevents full assessment."), context=_CTX_NO_RESOURCES)


def test_accepts_incomplete() -> None:
    validate_ai_output(_output("Analysis is incomplete due to empty inventory."), context=_CTX_NO_RESOURCES)


def test_accepts_empty_context() -> None:
    validate_ai_output(_output("empty context provided — cannot assess."), context=_CTX_NO_RESOURCES)


# ── case-insensitive ───────────────────────────────────────────────────────────

def test_case_insensitive_no_data() -> None:
    validate_ai_output(_output("NO DATA AVAILABLE for assessment."), context=_CTX_NO_RESOURCES)


def test_case_insensitive_missing_data() -> None:
    validate_ai_output(_output("Missing Data prevents resource analysis."), context=_CTX_NO_RESOURCES)


def test_case_insensitive_unavailable() -> None:
    validate_ai_output(_output("Resource inventory is UNAVAILABLE."), context=_CTX_NO_RESOURCES)


# ── invalid: no signal present ─────────────────────────────────────────────────

def test_rejects_output_with_no_limitation_signal() -> None:
    with pytest.raises(AIOutputValidationError, match="data limitations"):
        validate_ai_output(
            _output("Everything looks fine with the infrastructure."),
            context=_CTX_NO_RESOURCES,
        )


def test_rejects_partial_unrelated_words() -> None:
    with pytest.raises(AIOutputValidationError):
        validate_ai_output(
            _output("High availability architecture recommended."),
            context=_CTX_NO_RESOURCES,
        )


# ── resources_available=True — no signal required ─────────────────────────────

def test_no_signal_required_when_resources_available() -> None:
    validate_ai_output(
        _output("All resources analyzed successfully."),
        context=_CTX_WITH_RESOURCES,
    )


def test_signal_still_accepted_when_resources_available() -> None:
    validate_ai_output(
        _output("Some limitations noted but resources are available."),
        context=_CTX_WITH_RESOURCES,
    )


# ── LIMITATION_SIGNALS constant ────────────────────────────────────────────────

def test_limitation_signals_contains_expected_entries() -> None:
    required = {"limitation", "constraint", "no data", "unavailable", "not available", "missing data", "incomplete", "empty context"}
    assert required.issubset(set(LIMITATION_SIGNALS))


# ── no-regression: existing validator rules still enforced ────────────────────

def test_credential_pattern_still_blocked() -> None:
    with pytest.raises(AIOutputValidationError, match="credential"):
        validate_ai_output(
            "-----BEGIN PRIVATE KEY-----abc limitation noted",
            context=_CTX_NO_RESOURCES,
        )


def test_executed_action_still_blocked() -> None:
    with pytest.raises(AIOutputValidationError, match="action was executed"):
        validate_ai_output(
            "I deleted the instance. no data available.",
            context=_CTX_WITH_RESOURCES,
        )


def test_destructive_without_safety_still_blocked() -> None:
    with pytest.raises(AIOutputValidationError, match="destructive"):
        validate_ai_output(
            '{"executive_summary": {"summary": "We should terminate all underused instances."}}',
            context=_CTX_WITH_RESOURCES,
        )
