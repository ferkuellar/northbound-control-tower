from enum import StrEnum


class AIProvider(StrEnum):
    NONE = "none"
    DEEPSEEK = "deepseek"
    CLAUDE = "claude"
    OPENAI = "openai"


class AIAnalysisType(StrEnum):
    EXECUTIVE_SUMMARY = "executive_summary"
    TECHNICAL_ASSESSMENT = "technical_assessment"
    REMEDIATION_RECOMMENDATIONS = "remediation_recommendations"
    FULL_ASSESSMENT = "full_assessment"


class AIAnalysisStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
