class AIAnalysisError(Exception):
    """Base exception for AI analysis failures."""


class AIProviderConfigurationError(AIAnalysisError):
    """Raised when an AI provider is not configured safely."""


class AIOutputValidationError(AIAnalysisError):
    """Raised when an AI output fails safety validation."""
