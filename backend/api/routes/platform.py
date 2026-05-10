from fastapi import APIRouter

from api.schemas.platform import PlatformScopeResponse

router = APIRouter()


@router.get("/scope", response_model=PlatformScopeResponse)
def get_platform_scope() -> PlatformScopeResponse:
    return PlatformScopeResponse(
        clouds=["aws", "oci"],
        findings=[
            "idle_compute",
            "public_exposure",
            "missing_tags",
            "unattached_volumes",
            "observability_gaps",
        ],
        ai_features=[
            "executive_summaries",
            "technical_assessments",
            "remediation_recommendations",
        ],
        architecture="modular_monolith",
    )
