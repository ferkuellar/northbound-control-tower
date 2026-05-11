from __future__ import annotations

from collections.abc import Callable
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from collectors.aws.normalizers import (
    normalize_cloudwatch_alarm,
    normalize_ebs_volume,
    normalize_ec2_instance,
    normalize_iam_policy,
    normalize_iam_role,
    normalize_iam_user,
    normalize_rds_instance,
    normalize_s3_bucket,
    normalize_security_group,
    normalize_subnet,
    normalize_vpc,
)
from collectors.aws.session import AWSSessionFactory, aws_error_message, is_access_denied
from models.cloud_account import CloudAccount


class AWSInventoryCollector:
    def __init__(self, cloud_account: CloudAccount, *, timeout_seconds: int) -> None:
        self.cloud_account = cloud_account
        self.region = cloud_account.default_region
        self.session_factory = AWSSessionFactory(cloud_account, timeout_seconds=timeout_seconds)
        self.session = self.session_factory.create_session()
        self.partial_errors: list[dict[str, str]] = []

    def collect_all(self) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        collectors: list[Callable[[], list[dict[str, Any]]]] = [
            self.collect_ec2_instances,
            self.collect_ebs_volumes,
            self.collect_s3_buckets,
            self.collect_rds_instances,
            self.collect_iam_users_roles_policies_basic,
            self.collect_vpcs_subnets_security_groups,
            self.collect_cloudwatch_alarms_basic,
        ]
        resources: list[dict[str, Any]] = []
        for collect in collectors:
            resources.extend(collect())
        return resources, self.partial_errors

    def _client(self, service_name: str, region_name: str | None = None):
        return self.session.client(service_name, region_name=region_name or self.region, config=self.session_factory.client_config())

    def _record_partial_error(self, service: str, error: Exception) -> None:
        error_type = "access_denied" if is_access_denied(error) else "aws_error"
        self.partial_errors.append({"service": service, "type": error_type, "message": aws_error_message(error)})

    def _safe_collect(self, service: str, collect: Callable[[], list[dict[str, Any]]]) -> list[dict[str, Any]]:
        try:
            return collect()
        except (ClientError, BotoCoreError) as exc:
            self._record_partial_error(service, exc)
            return []

    def collect_ec2_instances(self) -> list[dict[str, Any]]:
        def collect() -> list[dict[str, Any]]:
            client = self._client("ec2")
            resources: list[dict[str, Any]] = []
            paginator = client.get_paginator("describe_instances")
            for page in paginator.paginate():
                for reservation in page.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        resources.append(normalize_ec2_instance(instance, self.region))
            return resources

        return self._safe_collect("ec2_instances", collect)

    def collect_ebs_volumes(self) -> list[dict[str, Any]]:
        def collect() -> list[dict[str, Any]]:
            client = self._client("ec2")
            resources: list[dict[str, Any]] = []
            paginator = client.get_paginator("describe_volumes")
            for page in paginator.paginate():
                for volume in page.get("Volumes", []):
                    resources.append(normalize_ebs_volume(volume, self.region))
            return resources

        return self._safe_collect("ebs_volumes", collect)

    def collect_s3_buckets(self) -> list[dict[str, Any]]:
        def collect() -> list[dict[str, Any]]:
            client = self._client("s3", region_name=self.region)
            response = client.list_buckets()
            return [normalize_s3_bucket(bucket, self.region) for bucket in response.get("Buckets", [])]

        return self._safe_collect("s3_buckets", collect)

    def collect_rds_instances(self) -> list[dict[str, Any]]:
        def collect() -> list[dict[str, Any]]:
            client = self._client("rds")
            resources: list[dict[str, Any]] = []
            paginator = client.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                for instance in page.get("DBInstances", []):
                    resources.append(normalize_rds_instance(instance, self.region))
            return resources

        return self._safe_collect("rds_instances", collect)

    def collect_iam_users_roles_policies_basic(self) -> list[dict[str, Any]]:
        def collect() -> list[dict[str, Any]]:
            client = self._client("iam", region_name="us-east-1")
            resources: list[dict[str, Any]] = []
            for page in client.get_paginator("list_users").paginate():
                resources.extend(normalize_iam_user(user) for user in page.get("Users", []))
            for page in client.get_paginator("list_roles").paginate():
                resources.extend(normalize_iam_role(role) for role in page.get("Roles", []))
            for page in client.get_paginator("list_policies").paginate(Scope="Local"):
                resources.extend(normalize_iam_policy(policy) for policy in page.get("Policies", []))
            return resources

        return self._safe_collect("iam_identity", collect)

    def collect_vpcs_subnets_security_groups(self) -> list[dict[str, Any]]:
        def collect() -> list[dict[str, Any]]:
            client = self._client("ec2")
            resources: list[dict[str, Any]] = []
            for page in client.get_paginator("describe_vpcs").paginate():
                resources.extend(normalize_vpc(vpc, self.region) for vpc in page.get("Vpcs", []))
            for page in client.get_paginator("describe_subnets").paginate():
                resources.extend(normalize_subnet(subnet, self.region) for subnet in page.get("Subnets", []))
            for page in client.get_paginator("describe_security_groups").paginate():
                resources.extend(normalize_security_group(group, self.region) for group in page.get("SecurityGroups", []))
            return resources

        return self._safe_collect("ec2_networking", collect)

    def collect_cloudwatch_alarms_basic(self) -> list[dict[str, Any]]:
        def collect() -> list[dict[str, Any]]:
            client = self._client("cloudwatch")
            resources: list[dict[str, Any]] = []
            paginator = client.get_paginator("describe_alarms")
            for page in paginator.paginate():
                for alarm in page.get("MetricAlarms", []):
                    resources.append(normalize_cloudwatch_alarm(alarm, self.region))
            return resources

        return self._safe_collect("cloudwatch_alarms", collect)
