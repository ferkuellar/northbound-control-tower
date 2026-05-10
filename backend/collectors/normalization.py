from models.normalized_resource import CloudProvider, NormalizedResource, ResourceType


def normalize_resource(
    *,
    provider: CloudProvider,
    resource_type: ResourceType,
    resource_id: str,
    region: str,
    name: str | None = None,
    account_id: str | None = None,
    tags: dict[str, str] | None = None,
    metadata: dict | None = None,
) -> NormalizedResource:
    return NormalizedResource(
        provider=provider,
        resource_type=resource_type,
        resource_id=resource_id,
        region=region,
        name=name,
        account_id=account_id,
        tags=tags or {},
        metadata=metadata or {},
    )
