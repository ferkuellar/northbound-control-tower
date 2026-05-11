from collectors.aws.normalizers import (
    AWSProviderNormalizer,
    normalize_cloudwatch_alarm,
    normalize_ebs_volume,
    normalize_ec2_instance,
    normalize_iam_user,
    normalize_rds_instance,
    normalize_s3_bucket,
    normalize_security_group,
    normalize_vpc,
)
from normalization.contracts import BaseProviderNormalizer


def test_normalize_ec2_instance() -> None:
    resource = normalize_ec2_instance(
        {
            "InstanceId": "i-123",
            "InstanceType": "t3.micro",
            "State": {"Name": "running"},
            "Placement": {"AvailabilityZone": "us-east-1a"},
            "Tags": [{"Key": "Name", "Value": "web-1"}],
            "VpcId": "vpc-123",
            "SubnetId": "subnet-123",
        },
        "us-east-1",
    )

    assert resource["provider"] == "aws"
    assert resource["resource_type"] == "compute"
    assert resource["resource_id"] == "i-123"
    assert resource["name"] == "web-1"
    assert resource["metadata"]["instance_type"] == "t3.micro"


def test_normalize_ebs_volume() -> None:
    resource = normalize_ebs_volume(
        {
            "VolumeId": "vol-123",
            "State": "available",
            "AvailabilityZone": "us-east-1a",
            "Size": 100,
            "VolumeType": "gp3",
            "Encrypted": True,
        },
        "us-east-1",
    )

    assert resource["resource_type"] == "block_storage"
    assert resource["resource_id"] == "vol-123"
    assert resource["metadata"]["encrypted"] is True


def test_normalize_s3_bucket() -> None:
    resource = normalize_s3_bucket({"Name": "nct-bucket"}, "us-east-1")

    assert resource["resource_type"] == "object_storage"
    assert resource["resource_id"] == "nct-bucket"
    assert resource["name"] == "nct-bucket"


def test_normalize_rds_instance() -> None:
    resource = normalize_rds_instance(
        {
            "DBInstanceArn": "arn:aws:rds:us-east-1:123:db:app",
            "DBInstanceIdentifier": "app-db",
            "DBInstanceStatus": "available",
            "Engine": "postgres",
            "EngineVersion": "16",
        },
        "us-east-1",
    )

    assert resource["resource_type"] == "database"
    assert resource["metadata"]["engine"] == "postgres"
    assert resource["metadata"]["engine_version"] == "16"


def test_normalize_iam_user() -> None:
    resource = normalize_iam_user({"Arn": "arn:aws:iam::123:user/alice", "UserName": "alice"})

    assert resource["resource_type"] == "identity"
    assert resource["region"] == "global"
    assert resource["name"] == "alice"


def test_normalize_vpc_and_security_group() -> None:
    vpc = normalize_vpc({"VpcId": "vpc-123", "State": "available", "CidrBlock": "10.0.0.0/16"}, "us-east-1")
    group = normalize_security_group({"GroupId": "sg-123", "GroupName": "web", "VpcId": "vpc-123"}, "us-east-1")

    assert vpc["resource_type"] == "network"
    assert vpc["metadata"]["cidr_block"] == "10.0.0.0/16"
    assert group["resource_id"] == "sg-123"


def test_normalize_cloudwatch_alarm() -> None:
    resource = normalize_cloudwatch_alarm(
        {"AlarmArn": "arn:aws:cloudwatch:us-east-1:123:alarm:cpu", "AlarmName": "cpu", "StateValue": "OK"},
        "us-east-1",
    )

    assert resource["resource_type"] == "monitoring"
    assert resource["status"] == "OK"


def test_aws_provider_normalizer_conforms_to_contract() -> None:
    assert isinstance(AWSProviderNormalizer(), BaseProviderNormalizer)
