from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from models.resource import ResourceType


def _tags_from_aws(tags: list[dict[str, Any]] | None) -> dict[str, str]:
    if not tags:
        return {}
    return {str(tag.get("Key")): str(tag.get("Value", "")) for tag in tags if tag.get("Key")}


def _base(
    *,
    resource_type: ResourceType,
    resource_id: str,
    raw_type: str,
    region: str | None,
    name: str | None = None,
    availability_zone: str | None = None,
    status: str | None = None,
    tags: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "provider": "aws",
        "resource_type": resource_type.value,
        "resource_id": resource_id,
        "name": name,
        "region": region,
        "availability_zone": availability_zone,
        "raw_type": raw_type,
        "status": status,
        "tags": tags or {},
        "metadata": metadata or {},
        "discovered_at": datetime.now(UTC),
    }


def normalize_ec2_instance(instance: dict[str, Any], region: str) -> dict[str, Any]:
    tags = _tags_from_aws(instance.get("Tags"))
    return _base(
        resource_type=ResourceType.COMPUTE,
        resource_id=instance["InstanceId"],
        name=tags.get("Name"),
        region=region,
        availability_zone=instance.get("Placement", {}).get("AvailabilityZone"),
        raw_type="AWS::EC2::Instance",
        status=instance.get("State", {}).get("Name"),
        tags=tags,
        metadata={
            "instance_type": instance.get("InstanceType"),
            "launch_time": str(instance.get("LaunchTime")) if instance.get("LaunchTime") else None,
            "private_ip_address": instance.get("PrivateIpAddress"),
            "public_ip_address": instance.get("PublicIpAddress"),
            "vpc_id": instance.get("VpcId"),
            "subnet_id": instance.get("SubnetId"),
        },
    )


def normalize_ebs_volume(volume: dict[str, Any], region: str) -> dict[str, Any]:
    tags = _tags_from_aws(volume.get("Tags"))
    return _base(
        resource_type=ResourceType.BLOCK_STORAGE,
        resource_id=volume["VolumeId"],
        name=tags.get("Name"),
        region=region,
        availability_zone=volume.get("AvailabilityZone"),
        raw_type="AWS::EC2::Volume",
        status=volume.get("State"),
        tags=tags,
        metadata={
            "size_gib": volume.get("Size"),
            "volume_type": volume.get("VolumeType"),
            "encrypted": volume.get("Encrypted"),
            "attachments": volume.get("Attachments", []),
        },
    )


def normalize_s3_bucket(bucket: dict[str, Any], region: str | None) -> dict[str, Any]:
    return _base(
        resource_type=ResourceType.OBJECT_STORAGE,
        resource_id=bucket["Name"],
        name=bucket["Name"],
        region=region,
        raw_type="AWS::S3::Bucket",
        status="available",
        metadata={"creation_date": str(bucket.get("CreationDate")) if bucket.get("CreationDate") else None},
    )


def normalize_rds_instance(instance: dict[str, Any], region: str) -> dict[str, Any]:
    return _base(
        resource_type=ResourceType.DATABASE,
        resource_id=instance["DBInstanceArn"],
        name=instance.get("DBInstanceIdentifier"),
        region=region,
        availability_zone=instance.get("AvailabilityZone"),
        raw_type="AWS::RDS::DBInstance",
        status=instance.get("DBInstanceStatus"),
        metadata={
            "engine": instance.get("Engine"),
            "engine_version": instance.get("EngineVersion"),
            "db_instance_class": instance.get("DBInstanceClass"),
            "multi_az": instance.get("MultiAZ"),
            "storage_encrypted": instance.get("StorageEncrypted"),
        },
    )


def normalize_iam_user(user: dict[str, Any]) -> dict[str, Any]:
    return _base(
        resource_type=ResourceType.IDENTITY,
        resource_id=user["Arn"],
        name=user.get("UserName"),
        region="global",
        raw_type="AWS::IAM::User",
        status="active",
        metadata={"user_id": user.get("UserId"), "create_date": str(user.get("CreateDate")) if user.get("CreateDate") else None},
    )


def normalize_iam_role(role: dict[str, Any]) -> dict[str, Any]:
    return _base(
        resource_type=ResourceType.IDENTITY,
        resource_id=role["Arn"],
        name=role.get("RoleName"),
        region="global",
        raw_type="AWS::IAM::Role",
        status="active",
        metadata={"role_id": role.get("RoleId"), "create_date": str(role.get("CreateDate")) if role.get("CreateDate") else None},
    )


def normalize_iam_policy(policy: dict[str, Any]) -> dict[str, Any]:
    return _base(
        resource_type=ResourceType.IDENTITY,
        resource_id=policy["Arn"],
        name=policy.get("PolicyName"),
        region="global",
        raw_type="AWS::IAM::Policy",
        status="active",
        metadata={"attachment_count": policy.get("AttachmentCount"), "is_attachable": policy.get("IsAttachable")},
    )


def normalize_vpc(vpc: dict[str, Any], region: str) -> dict[str, Any]:
    tags = _tags_from_aws(vpc.get("Tags"))
    return _base(
        resource_type=ResourceType.NETWORK,
        resource_id=vpc["VpcId"],
        name=tags.get("Name"),
        region=region,
        raw_type="AWS::EC2::VPC",
        status=vpc.get("State"),
        tags=tags,
        metadata={"cidr_block": vpc.get("CidrBlock"), "is_default": vpc.get("IsDefault")},
    )


def normalize_subnet(subnet: dict[str, Any], region: str) -> dict[str, Any]:
    tags = _tags_from_aws(subnet.get("Tags"))
    return _base(
        resource_type=ResourceType.NETWORK,
        resource_id=subnet["SubnetId"],
        name=tags.get("Name"),
        region=region,
        availability_zone=subnet.get("AvailabilityZone"),
        raw_type="AWS::EC2::Subnet",
        status=subnet.get("State"),
        tags=tags,
        metadata={"vpc_id": subnet.get("VpcId"), "cidr_block": subnet.get("CidrBlock")},
    )


def normalize_security_group(group: dict[str, Any], region: str) -> dict[str, Any]:
    tags = _tags_from_aws(group.get("Tags"))
    return _base(
        resource_type=ResourceType.NETWORK,
        resource_id=group["GroupId"],
        name=group.get("GroupName"),
        region=region,
        raw_type="AWS::EC2::SecurityGroup",
        status="available",
        tags=tags,
        metadata={"vpc_id": group.get("VpcId"), "description": group.get("Description")},
    )


def normalize_cloudwatch_alarm(alarm: dict[str, Any], region: str) -> dict[str, Any]:
    return _base(
        resource_type=ResourceType.MONITORING,
        resource_id=alarm["AlarmArn"],
        name=alarm.get("AlarmName"),
        region=region,
        raw_type="AWS::CloudWatch::Alarm",
        status=alarm.get("StateValue"),
        metadata={
            "metric_name": alarm.get("MetricName"),
            "namespace": alarm.get("Namespace"),
            "comparison_operator": alarm.get("ComparisonOperator"),
        },
    )
