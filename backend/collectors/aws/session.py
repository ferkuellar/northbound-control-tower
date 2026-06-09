from __future__ import annotations

import re

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from models.cloud_account import CloudAccount, CloudAccountAuthType
from security.encryption import decrypt_credential

# Characters valid in AWS RoleSessionName: alphanumeric plus =,.@-_
_INVALID_SESSION_CHARS = re.compile(r"[^\w=,.@\-]")


def build_role_session_name(
    *,
    user_id: str | None = None,
    operation: str = "scan",
    request_number: str | None = None,
) -> str:
    actor = str(user_id or "svc")[:8]
    safe_operation = operation.replace("_", "-")[:24]
    name = f"nb-{actor}-{safe_operation}-{request_number}" if request_number else f"nb-{actor}-{safe_operation}"
    return _INVALID_SESSION_CHARS.sub("", name)[:64]


class AWSSessionFactory:
    """Creates AWS boto3 sessions for a given CloudAccount.

    For passive scan/inventory operations use the default (role_arn).
    For Terraform apply/remediation use role_arn_override=cloud_account.remediation_role_arn
    via get_aws_remediation_session() — never pass remediation_role_arn silently.
    """

    def __init__(
        self,
        cloud_account: CloudAccount,
        *,
        timeout_seconds: int,
        user_id: str | None = None,
        operation: str = "scan",
        role_arn_override: str | None = None,
    ) -> None:
        self.cloud_account = cloud_account
        self.timeout_seconds = timeout_seconds
        self.user_id = user_id
        self.operation = operation
        self.role_arn_override = role_arn_override

    def create_session(self) -> boto3.Session:
        auth_type = CloudAccountAuthType(self.cloud_account.auth_type)
        if auth_type == CloudAccountAuthType.ACCESS_KEYS:
            return boto3.Session(
                aws_access_key_id=self.cloud_account.access_key_id,
                aws_secret_access_key=decrypt_credential(self.cloud_account.secret_access_key),
                region_name=self.cloud_account.default_region,
            )
        if auth_type == CloudAccountAuthType.ROLE_ARN:
            role_arn = self.role_arn_override or self.cloud_account.role_arn
            base_session = boto3.Session(region_name=self.cloud_account.default_region)
            sts_client = base_session.client("sts", config=self.client_config())
            assume_role_args = {
                "RoleArn": role_arn,
                "RoleSessionName": build_role_session_name(user_id=self.user_id, operation=self.operation),
            }
            if self.cloud_account.external_id:
                assume_role_args["ExternalId"] = self.cloud_account.external_id
            response = sts_client.assume_role(**assume_role_args)
            credentials = response["Credentials"]
            return boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=self.cloud_account.default_region,
            )
        return boto3.Session(region_name=self.cloud_account.default_region)

    def client_config(self) -> Config:
        return Config(
            connect_timeout=min(self.timeout_seconds, 60),
            read_timeout=self.timeout_seconds,
            retries={"max_attempts": 3, "mode": "standard"},
        )


def get_aws_readonly_session(
    cloud_account: CloudAccount,
    *,
    timeout_seconds: int,
    user_id: str | None = None,
    operation: str = "scan",
) -> boto3.Session:
    """Create a session using role_arn — for collectors and inventory scans only."""
    return AWSSessionFactory(
        cloud_account,
        timeout_seconds=timeout_seconds,
        user_id=user_id,
        operation=operation,
    ).create_session()


def get_aws_remediation_session(
    cloud_account: CloudAccount,
    *,
    timeout_seconds: int,
    user_id: str | None = None,
    operation: str = "apply",
) -> boto3.Session:
    """Create a session using remediation_role_arn — for Terraform apply only.

    Raises ValueError if remediation_role_arn is not configured.
    Never falls back to role_arn.
    """
    if not cloud_account.remediation_role_arn:
        raise ValueError(
            "Terraform apply requires remediation_role_arn to be configured "
            "for this cloud account. "
            "Set the northbound-remediation IAM role ARN before enabling apply."
        )
    return AWSSessionFactory(
        cloud_account,
        timeout_seconds=timeout_seconds,
        user_id=user_id,
        operation=operation,
        role_arn_override=cloud_account.remediation_role_arn,
    ).create_session()


def is_access_denied(error: Exception) -> bool:
    if not isinstance(error, ClientError):
        return False
    code = error.response.get("Error", {}).get("Code", "")
    return code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "UnrecognizedClientException"}


def aws_error_message(error: Exception) -> str:
    if isinstance(error, ClientError):
        details = error.response.get("Error", {})
        code = details.get("Code", "AWSClientError")
        message = details.get("Message", str(error))
        return f"{code}: {message}"
    if isinstance(error, BotoCoreError):
        return str(error)
    return str(error)
