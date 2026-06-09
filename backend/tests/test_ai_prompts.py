"""Tests for ai/prompts.py — SYSTEM_PROMPT, EXECUTIVE_SUMMARY_SCHEMA, example, and prompt builder."""
from __future__ import annotations

from ai.enums import AIAnalysisType
from ai.prompts import (
    EXECUTIVE_SUMMARY_EXAMPLE,
    EXECUTIVE_SUMMARY_SCHEMA,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_prompt,
)


# ── PROMPT_VERSION ─────────────────────────────────────────────────────────────

def test_prompt_version_exists() -> None:
    assert PROMPT_VERSION


def test_prompt_version_is_phase9_v1_1() -> None:
    assert PROMPT_VERSION == "phase9-v1.1"


# ── SYSTEM_PROMPT content ─────────────────────────────────────────────────────

def test_system_prompt_role_principal_cloud_architect() -> None:
    assert "Principal Cloud Architect" in SYSTEM_PROMPT


def test_system_prompt_audience_ciso_cfo() -> None:
    assert "CISO or CFO" in SYSTEM_PROMPT


def test_system_prompt_never_invent() -> None:
    assert "Never invent" in SYSTEM_PROMPT


def test_system_prompt_json_only() -> None:
    assert "valid JSON only" in SYSTEM_PROMPT


def test_system_prompt_parseable_by_json_loads() -> None:
    assert "parseable by json.loads()" in SYSTEM_PROMPT


def test_system_prompt_no_markdown_fences() -> None:
    assert "no markdown fences" in SYSTEM_PROMPT


def test_system_prompt_no_preamble() -> None:
    assert "no preamble" in SYSTEM_PROMPT


def test_system_prompt_destructive_safety_language() -> None:
    assert "approval" in SYSTEM_PROMPT
    assert "backup" in SYSTEM_PROMPT
    assert "snapshot" in SYSTEM_PROMPT
    assert "rollback" in SYSTEM_PROMPT


# ── EXECUTIVE_SUMMARY_SCHEMA structure ────────────────────────────────────────

def test_schema_has_executive_summary_key() -> None:
    assert "executive_summary" in EXECUTIVE_SUMMARY_SCHEMA


def test_schema_has_overall_posture() -> None:
    assert "overall_posture" in EXECUTIVE_SUMMARY_SCHEMA


def test_schema_has_business_risk() -> None:
    assert "business_risk" in EXECUTIVE_SUMMARY_SCHEMA


def test_schema_has_domain_highlights() -> None:
    assert "domain_highlights" in EXECUTIVE_SUMMARY_SCHEMA


def test_schema_has_recommendations_30_60_90() -> None:
    assert "recommendations_30_60_90" in EXECUTIVE_SUMMARY_SCHEMA


def test_schema_has_limitations() -> None:
    assert "limitations" in EXECUTIVE_SUMMARY_SCHEMA


def test_schema_has_days_30_60_90() -> None:
    assert "days_30" in EXECUTIVE_SUMMARY_SCHEMA
    assert "days_60" in EXECUTIVE_SUMMARY_SCHEMA
    assert "days_90" in EXECUTIVE_SUMMARY_SCHEMA


def test_schema_has_risk_level_field() -> None:
    assert "risk_level" in EXECUTIVE_SUMMARY_SCHEMA


def test_schema_has_top_risks() -> None:
    assert "top_risks" in EXECUTIVE_SUMMARY_SCHEMA


# ── EXECUTIVE_SUMMARY_EXAMPLE ─────────────────────────────────────────────────

def test_example_warns_values_are_fictitious() -> None:
    assert "fictitious" in EXECUTIVE_SUMMARY_EXAMPLE.lower()


def test_example_clarifies_do_not_copy_without_context() -> None:
    lowered = EXECUTIVE_SUMMARY_EXAMPLE.lower()
    assert "do not copy" in lowered or "not copy" in lowered


def test_example_has_executive_summary_structure() -> None:
    assert "executive_summary" in EXECUTIVE_SUMMARY_EXAMPLE


def test_example_has_all_required_sections() -> None:
    assert "overall_posture" in EXECUTIVE_SUMMARY_EXAMPLE
    assert "business_risk" in EXECUTIVE_SUMMARY_EXAMPLE
    assert "domain_highlights" in EXECUTIVE_SUMMARY_EXAMPLE
    assert "recommendations_30_60_90" in EXECUTIVE_SUMMARY_EXAMPLE
    assert "limitations" in EXECUTIVE_SUMMARY_EXAMPLE


def test_example_has_recommendations_buckets() -> None:
    assert "days_30" in EXECUTIVE_SUMMARY_EXAMPLE
    assert "days_60" in EXECUTIVE_SUMMARY_EXAMPLE
    assert "days_90" in EXECUTIVE_SUMMARY_EXAMPLE


# ── executive_summary prompt integration ──────────────────────────────────────

def test_executive_summary_prompt_includes_schema() -> None:
    prompt = build_prompt(AIAnalysisType.EXECUTIVE_SUMMARY, {})
    assert "executive_summary" in prompt
    assert "overall_posture" in prompt
    assert "domain_highlights" in prompt
    assert "recommendations_30_60_90" in prompt
    assert "limitations" in prompt


def test_executive_summary_prompt_includes_example() -> None:
    prompt = build_prompt(AIAnalysisType.EXECUTIVE_SUMMARY, {})
    assert "fictitious" in prompt.lower()


def test_executive_summary_prompt_includes_prompt_version() -> None:
    prompt = build_prompt(AIAnalysisType.EXECUTIVE_SUMMARY, {})
    assert PROMPT_VERSION in prompt


def test_executive_summary_prompt_includes_days_60_structure() -> None:
    prompt = build_prompt(AIAnalysisType.EXECUTIVE_SUMMARY, {})
    assert "days_60" in prompt
    assert "risk_if_skipped" in prompt


# ── other analysis types still produce prompts ───────────────────────────────

def test_technical_assessment_prompt_builds() -> None:
    prompt = build_prompt(AIAnalysisType.TECHNICAL_ASSESSMENT, {})
    assert "technical_assessment" in prompt


def test_remediation_recommendations_prompt_builds() -> None:
    prompt = build_prompt(AIAnalysisType.REMEDIATION_RECOMMENDATIONS, {})
    assert "remediation_recommendations" in prompt


def test_full_assessment_prompt_builds() -> None:
    prompt = build_prompt(AIAnalysisType.FULL_ASSESSMENT, {})
    assert "full_assessment" in prompt
