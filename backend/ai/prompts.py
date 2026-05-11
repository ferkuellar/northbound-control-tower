import json
from typing import Any

from ai.enums import AIAnalysisType

PROMPT_VERSION = "phase9-v1"

BASE_RULES = """
Use only the provided context. Do not invent resources, costs, findings, scores, providers, compliance certifications, or actions.
AI explains and recommends; deterministic engines decide. Do not modify scores or claim remediation was executed.
If data is missing, explicitly state limitations.
Do not recommend destructive changes without approval, backup, snapshot, and rollback validation language.
Return structured JSON with keys relevant to the requested analysis.
"""


def _context_block(context: dict[str, Any]) -> str:
    return json.dumps(context, indent=2, sort_keys=True, default=str)


def executive_summary_prompt(context: dict[str, Any]) -> str:
    return f"""{BASE_RULES}
Produce an executive_summary with business_risk, domain_highlights, and recommendations_30_60_90.
Use concise leadership language.
Context:
{_context_block(context)}
"""


def technical_assessment_prompt(context: dict[str, Any]) -> str:
    return f"""{BASE_RULES}
Produce a technical_assessment covering findings interpretation, architecture implications, operational weaknesses, provider-specific notes, constraints, and assumptions.
Context:
{_context_block(context)}
"""


def remediation_recommendations_prompt(context: dict[str, Any]) -> str:
    return f"""{BASE_RULES}
Produce remediation_recommendations as a prioritized list with severity, effort, expected_impact, suggested_owner, and safe remediation language.
Context:
{_context_block(context)}
"""


def full_assessment_prompt(context: dict[str, Any]) -> str:
    return f"""{BASE_RULES}
Produce a full_assessment with executive_summary, technical_assessment, remediation_recommendations, and limitations.
Context:
{_context_block(context)}
"""


def build_prompt(analysis_type: AIAnalysisType, context: dict[str, Any]) -> str:
    templates = {
        AIAnalysisType.EXECUTIVE_SUMMARY: executive_summary_prompt,
        AIAnalysisType.TECHNICAL_ASSESSMENT: technical_assessment_prompt,
        AIAnalysisType.REMEDIATION_RECOMMENDATIONS: remediation_recommendations_prompt,
        AIAnalysisType.FULL_ASSESSMENT: full_assessment_prompt,
    }
    return templates[analysis_type](context)
