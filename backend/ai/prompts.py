import json
from typing import Any

from ai.enums import AIAnalysisType

PROMPT_VERSION = "phase9-v1.1"

SYSTEM_PROMPT = (
    "You are a Principal Cloud Architect at Northbound FinOps delivering "
    "a formal consulting assessment. Your audience is a CISO or CFO — not a developer.\n"
    "Rules:\n"
    "- Use only the provided context. Never invent data — no invented resources, costs, findings, or scores.\n"
    "- Translate technical findings into business risk language.\n"
    "- Quantify impact when data supports it (affected resources, estimated exposure).\n"
    "- Every destructive recommendation must include: approval, backup, snapshot, rollback.\n"
    "- Respond with valid JSON only — no markdown fences, no preamble, no explanation outside JSON.\n"
    "- Your entire response must be parseable by json.loads()."
)

EXECUTIVE_SUMMARY_SCHEMA = """\
Return exactly this JSON structure (no extra keys, no missing keys):
{
  "executive_summary": {
    "overall_posture": {
      "risk_level": "<critical|high|medium|low>",
      "one_line": "<single non-technical sentence — no AWS/OCI jargon>",
      "score_context": "<what the overall score means in business terms>"
    },
    "business_risk": {
      "summary": "<2-3 sentences: business impact, not technical detail>",
      "top_risks": [{
        "risk": "<business risk name>",
        "affected_assets": "<integer>",
        "impact": "<consequence if not addressed>",
        "urgency": "<immediate|30-days|60-days>"
      }]
    },
    "domain_highlights": [{
      "domain": "<finops|governance|observability|security_baseline|resilience>",
      "score": "<integer 0-100>",
      "grade": "<A|B|C|D|F>",
      "headline": "<one sentence — business meaning of this score>",
      "top_finding": "<most critical finding in this domain, or null>"
    }],
    "recommendations_30_60_90": {
      "days_30": [{
        "action": "<specific, actionable>",
        "owner": "<Security team|DevOps|FinOps|Cloud team>",
        "effort": "<hours|days>",
        "risk_if_skipped": "<business consequence>"
      }],
      "days_60": [{
        "action": "<specific, actionable>",
        "owner": "<Security team|DevOps|FinOps|Cloud team>",
        "effort": "<hours|days>",
        "risk_if_skipped": "<business consequence>"
      }],
      "days_90": [{
        "action": "<specific, actionable>",
        "owner": "<Security team|DevOps|FinOps|Cloud team>",
        "effort": "<hours|days>",
        "risk_if_skipped": "<business consequence>"
      }]
    },
    "limitations": ["<data gaps or caveats — empty array if none>"]
  }
}"""

EXECUTIVE_SUMMARY_EXAMPLE = """\
Canonical example. Values are fictitious — do not copy these values unless supported by the provided context.

{
  "executive_summary": {
    "overall_posture": {
      "risk_level": "high",
      "one_line": "The environment has material operational and governance risk that should be addressed before expanding production usage.",
      "score_context": "An overall score of 49 indicates weak control maturity, with security and governance gaps that can increase outage, audit, and exposure risk."
    },
    "business_risk": {
      "summary": "The current posture suggests that critical production assets may be exposed or poorly governed. If left unresolved, the organization could face service disruption, unauthorized access, audit findings, and avoidable remediation cost.",
      "top_risks": [
        {
          "risk": "Public exposure of production compute",
          "affected_assets": 1,
          "impact": "Increases likelihood of unauthorized access attempts and emergency remediation work.",
          "urgency": "immediate"
        }
      ]
    },
    "domain_highlights": [
      {
        "domain": "security_baseline",
        "score": 42,
        "grade": "D",
        "headline": "Security controls are below an acceptable production baseline.",
        "top_finding": "EC2 instance publicly accessible without WAF"
      },
      {
        "domain": "governance",
        "score": 55,
        "grade": "C",
        "headline": "Governance is inconsistent and may limit accountability across cloud assets.",
        "top_finding": "Resource missing required governance tags"
      }
    ],
    "recommendations_30_60_90": {
      "days_30": [
        {
          "action": "Restrict public exposure on the affected production compute resource after approval, backup, snapshot, and rollback validation.",
          "owner": "Security team",
          "effort": "days",
          "risk_if_skipped": "The resource remains exposed and may trigger incident response or audit escalation."
        }
      ],
      "days_60": [
        {
          "action": "Standardize required governance tags across production resources and validate ownership coverage.",
          "owner": "Cloud team",
          "effort": "days",
          "risk_if_skipped": "Cost, ownership, and remediation accountability remain unclear."
        }
      ],
      "days_90": [
        {
          "action": "Implement continuous posture monitoring for security baseline and governance score regression.",
          "owner": "DevOps",
          "effort": "days",
          "risk_if_skipped": "Control drift may go undetected until the next manual review or audit."
        }
      ]
    },
    "limitations": [
      "This example is fictitious and only demonstrates the expected format and tone."
    ]
  }
}"""

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
    return f"""Prompt version: {PROMPT_VERSION}

You are preparing an executive cloud posture summary for leadership.

Use the context below as the only source of truth:
{_context_block(context)}

{EXECUTIVE_SUMMARY_SCHEMA}

{EXECUTIVE_SUMMARY_EXAMPLE}

Rules:
- Return JSON only. Follow the schema exactly.
- Do not invent resources, scores, costs, or findings not present in the context above.
- If data is missing or incomplete, state it in the limitations array.
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
