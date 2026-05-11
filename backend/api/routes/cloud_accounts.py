from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas.inventory import AWSCloudAccountCreate, CloudAccountRead, OCICloudAccountCreate
from auth.dependencies import get_current_user, require_roles
from core.config import settings
from core.database import get_db
from models.cloud_account import CloudAccount, CloudAccountAuthType, CloudProvider
from models.user import User, UserRole
from services.audit_log import create_audit_log

router = APIRouter()


def _request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _request_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.post("/aws", response_model=CloudAccountRead, status_code=status.HTTP_201_CREATED)
def create_aws_cloud_account(
    payload: AWSCloudAccountCreate,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> CloudAccount:
    if payload.auth_type == CloudAccountAuthType.ACCESS_KEYS and (
        not payload.access_key_id or not payload.secret_access_key
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Access key credentials are required")
    if payload.auth_type == CloudAccountAuthType.ROLE_ARN and not payload.role_arn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role ARN is required")

    cloud_account = CloudAccount(
        tenant_id=current_user.tenant_id,
        provider=CloudProvider.AWS.value,
        name=payload.name,
        auth_type=payload.auth_type.value,
        access_key_id=payload.access_key_id,
        secret_access_key=payload.secret_access_key,
        role_arn=payload.role_arn,
        external_id=payload.external_id,
        default_region=payload.default_region or settings.aws_default_region,
        is_active=True,
    )
    db.add(cloud_account)
    db.flush()
    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="aws_cloud_account_created",
        resource_type="cloud_account",
        resource_id=str(cloud_account.id),
        metadata={"auth_type": cloud_account.auth_type, "region": cloud_account.default_region},
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
    )
    db.commit()
    db.refresh(cloud_account)
    return cloud_account


@router.post("/oci", response_model=CloudAccountRead, status_code=status.HTTP_201_CREATED)
def create_oci_cloud_account(
    payload: OCICloudAccountCreate,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> CloudAccount:
    if payload.auth_type not in {CloudAccountAuthType.OCI_CONFIG, CloudAccountAuthType.OCI_API_KEY}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OCI auth_type must be oci_config or oci_api_key")
    if payload.auth_type == CloudAccountAuthType.OCI_API_KEY:
        missing_fields = [
            field_name
            for field_name, value in {
                "tenancy_ocid": payload.tenancy_ocid,
                "user_ocid": payload.user_ocid,
                "fingerprint": payload.fingerprint,
                "private_key": payload.private_key,
                "region": payload.region,
            }.items()
            if not value
        ]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing OCI API key fields: {', '.join(missing_fields)}",
            )

    region = payload.region or settings.oci_default_region
    cloud_account = CloudAccount(
        tenant_id=current_user.tenant_id,
        provider=CloudProvider.OCI.value,
        name=payload.name,
        auth_type=payload.auth_type.value,
        default_region=region,
        tenancy_ocid=payload.tenancy_ocid,
        user_ocid=payload.user_ocid,
        fingerprint=payload.fingerprint,
        private_key=payload.private_key,
        private_key_passphrase=payload.private_key_passphrase,
        region=region,
        compartment_ocid=payload.compartment_ocid,
        is_active=True,
    )
    db.add(cloud_account)
    db.flush()
    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="oci_cloud_account_created",
        resource_type="cloud_account",
        resource_id=str(cloud_account.id),
        metadata={
            "auth_type": cloud_account.auth_type,
            "region": cloud_account.region,
            "has_compartment_scope": bool(cloud_account.compartment_ocid),
        },
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
    )
    db.commit()
    db.refresh(cloud_account)
    return cloud_account


@router.get("", response_model=list[CloudAccountRead])
def list_cloud_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CloudAccount]:
    return list(
        db.scalars(
            select(CloudAccount)
            .where(CloudAccount.tenant_id == current_user.tenant_id)
            .order_by(CloudAccount.created_at.desc())
        )
    )
