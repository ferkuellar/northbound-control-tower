from __future__ import annotations

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from models.cloud_account import CloudAccount, CloudAccountAuthType


class AWSSessionFactory:
    def __init__(self, cloud_account: CloudAccount, *, timeout_seconds: int) -> None:
        self.cloud_account = cloud_account
        self.timeout_seconds = timeout_seconds

    def create_session(self) -> boto3.Session:
        auth_type = CloudAccountAuthType(self.cloud_account.auth_type)
        if auth_type == CloudAccountAuthType.ACCESS_KEYS:
            return boto3.Session(
                aws_access_key_id=self.cloud_account.access_key_id,
                aws_secret_access_key=self.cloud_account.secret_access_key,
                region_name=self.cloud_account.default_region,
            )
        if auth_type == CloudAccountAuthType.ROLE_ARN:
            base_session = boto3.Session(region_name=self.cloud_account.default_region)
            sts_client = base_session.client("sts", config=self.client_config())
            assume_role_args = {
                "RoleArn": self.cloud_account.role_arn,
                "RoleSessionName": "northbound-control-tower-inventory",
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
