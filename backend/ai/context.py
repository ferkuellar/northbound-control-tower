from pydantic import BaseModel


class AIAnalysisContext(BaseModel):
    executive_summary_inputs: list[str]
    technical_assessment_inputs: list[str]
    remediation_inputs: list[str]


def build_empty_phase0_context() -> AIAnalysisContext:
    return AIAnalysisContext(
        executive_summary_inputs=[],
        technical_assessment_inputs=[],
        remediation_inputs=[],
    )
