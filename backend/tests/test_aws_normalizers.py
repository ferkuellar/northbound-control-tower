from collectors.aws.normalizers import normalize_ebs_volume, normalize_ec2_instance, normalize_s3_bucket


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
