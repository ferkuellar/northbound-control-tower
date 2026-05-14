import pytest

from provisioning.checkov_parser import CheckovParser
from provisioning.infracost_parser import InfracostParser


def test_checkov_parser_counts_and_blocking_findings() -> None:
    payload = {
        "results": {
            "passed_checks": [{}, {}],
            "failed_checks": [
                {
                    "check_id": "CKV_AWS_1",
                    "check_name": "S3 bucket allows public access",
                    "resource": "aws_s3_bucket.demo",
                    "file_path": "/main.tf",
                    "file_line_range": [1, 5],
                }
            ],
            "skipped_checks": [{}],
        }
    }

    summary = CheckovParser().parse(payload)

    assert summary["passed_count"] == 2
    assert summary["failed_count"] == 1
    assert summary["skipped_count"] == 1
    assert summary["highest_severity"] == "CRITICAL"
    assert summary["blocking_findings_count"] == 1
    assert summary["failed_checks"][0]["resource"] == "aws_s3_bucket.demo"


def test_checkov_parser_handles_empty_invalid_and_unknown() -> None:
    parser = CheckovParser()

    assert parser.parse({})["highest_severity"] == "UNKNOWN"
    with pytest.raises(ValueError):
        parser.parse_text("{bad json")

    summary = parser.parse({"results": {"failed_checks": [{"check_name": "custom advisory"}]}})
    assert summary["highest_severity"] == "UNKNOWN"


def test_infracost_parser_extracts_costs_and_resources() -> None:
    payload = {
        "currency": "USD",
        "totalMonthlyCost": "12.42",
        "totalHourlyCost": "0.017",
        "pastTotalMonthlyCost": "0",
        "diffTotalMonthlyCost": "12.42",
        "projects": [
            {
                "breakdown": {
                    "resources": [
                        {"name": "aws_instance.demo", "resourceType": "aws_instance", "monthlyCost": "12.42"},
                        {"name": "unsupported.demo", "resourceType": "custom", "monthlyCost": None},
                    ]
                }
            }
        ],
    }

    summary = InfracostParser().parse(payload)

    assert summary["currency"] == "USD"
    assert summary["total_monthly_cost"] == "12.42"
    assert summary["diff_total_monthly_cost"] == "12.42"
    assert summary["resources_count"] == 2
    assert summary["unsupported_resources_count"] == 1


def test_infracost_parser_handles_missing_and_invalid() -> None:
    parser = InfracostParser()

    assert parser.parse({})["available"] is False
    with pytest.raises(ValueError):
        parser.parse_text("{bad json")
