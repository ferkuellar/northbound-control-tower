from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TerraformTemplateDefinition:
    key: str
    provider: str
    finding_types: tuple[str, ...]
    title: str
    description: str
    risk_level: str
    required_variables: tuple[str, ...] = field(default_factory=tuple)
    module_path: str = ""


TEMPLATE_CATALOG: dict[str, TerraformTemplateDefinition] = {
    "cloud-public-exposure-review": TerraformTemplateDefinition(
        key="cloud-public-exposure-review",
        provider="multi",
        finding_types=("public_exposure",),
        title="Public exposure review",
        description="Prepare a governed review for public exposure remediation. No Terraform execution in Phase B.",
        risk_level="HIGH",
        required_variables=("resource_id", "provider", "finding_id"),
        module_path="terraform/templates/public-exposure-review",
    ),
    "cloud-volume-snapshot-and-cleanup": TerraformTemplateDefinition(
        key="cloud-volume-snapshot-and-cleanup",
        provider="multi",
        finding_types=("unattached_volume",),
        title="Snapshot and cleanup unattached volume",
        description="Prepare a snapshot-before-delete workflow draft for unattached volumes.",
        risk_level="MEDIUM",
        required_variables=("resource_id", "provider", "finding_id"),
        module_path="terraform/templates/volume-cleanup",
    ),
    "cloud-tagging-governance": TerraformTemplateDefinition(
        key="cloud-tagging-governance",
        provider="multi",
        finding_types=("missing_tags",),
        title="Tagging governance remediation",
        description="Prepare tag inputs for missing environment, owner, cost center and application metadata.",
        risk_level="LOW",
        required_variables=("resource_id", "provider", "finding_id"),
        module_path="terraform/templates/tagging-governance",
    ),
    "cloud-monitoring-baseline": TerraformTemplateDefinition(
        key="cloud-monitoring-baseline",
        provider="multi",
        finding_types=("observability_gap",),
        title="Monitoring baseline",
        description="Prepare a monitoring baseline request for resources lacking observability signals.",
        risk_level="MEDIUM",
        required_variables=("resource_id", "provider", "finding_id"),
        module_path="terraform/templates/monitoring-baseline",
    ),
}


def template_for_finding_type(finding_type: str, provider: str) -> TerraformTemplateDefinition:
    for template in TEMPLATE_CATALOG.values():
        if finding_type in template.finding_types:
            return template
    key = f"{provider}-{finding_type}".replace("_", "-")
    return TerraformTemplateDefinition(
        key=key,
        provider=provider,
        finding_types=(finding_type,),
        title=f"{provider.upper()} {finding_type.replace('_', ' ')} remediation draft",
        description="Generic remediation request draft. Template implementation is future work.",
        risk_level="MEDIUM",
        required_variables=("resource_id", "provider", "finding_id"),
        module_path=f"terraform/templates/{key}",
    )


def get_template(key: str) -> TerraformTemplateDefinition | None:
    return TEMPLATE_CATALOG.get(key)

