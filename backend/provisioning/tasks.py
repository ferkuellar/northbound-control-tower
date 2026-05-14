from __future__ import annotations

from core.database import SessionLocal
from models.provisioning_request import ProvisioningRequest
from provisioning.terraform_runner import TerraformRunner


def run_terraform_validate(request_id: str) -> None:
    db = SessionLocal()
    try:
        request = db.get(ProvisioningRequest, request_id)
        if request is not None:
            TerraformRunner(db).validate(request)
    finally:
        db.close()


def run_terraform_plan(request_id: str) -> None:
    db = SessionLocal()
    try:
        request = db.get(ProvisioningRequest, request_id)
        if request is not None:
            TerraformRunner(db).plan(request)
    finally:
        db.close()
