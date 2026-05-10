from pydantic import BaseModel, Field


class PlatformScopeResponse(BaseModel):
    clouds: list[str] = Field(..., description="Cloud providers enabled in the initial platform scope.")
    findings: list[str] = Field(..., description="Deterministic findings enabled in the initial platform scope.")
    ai_features: list[str] = Field(..., description="AI-assisted analysis features enabled in the initial platform scope.")
    architecture: str = Field(..., description="Current backend deployment architecture.")
