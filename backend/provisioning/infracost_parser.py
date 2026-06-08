from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any


class InfracostParser:
    def parse_text(self, value: str) -> dict[str, Any]:
        if not value.strip():
            return self._empty_summary(unavailable_reason="empty Infracost JSON")
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("Infracost JSON is invalid.") from exc
        return self.parse(payload)

    def parse(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return self._empty_summary(unavailable_reason="empty Infracost JSON")

        projects = payload.get("projects") or []
        total_monthly = self._decimal(payload.get("totalMonthlyCost"))
        total_hourly = self._decimal(payload.get("totalHourlyCost"))
        past_monthly = self._decimal(payload.get("pastTotalMonthlyCost"))
        diff_monthly = self._decimal(payload.get("diffTotalMonthlyCost"))
        resources: list[dict[str, Any]] = []
        unsupported = 0

        for project in projects:
            for resource in project.get("breakdown", {}).get("resources", []) or []:
                if not isinstance(resource, dict):
                    continue
                monthly = self._decimal(resource.get("monthlyCost"))
                resources.append(
                    {
                        "name": resource.get("name"),
                        "resource_type": resource.get("resourceType"),
                        "monthly_cost": self._string(monthly),
                    }
                )
                if monthly is None:
                    unsupported += 1

        return {
            "currency": payload.get("currency") or "USD",
            "total_monthly_cost": self._string(total_monthly),
            "total_hourly_cost": self._string(total_hourly),
            "past_total_monthly_cost": self._string(past_monthly),
            "diff_total_monthly_cost": self._string(diff_monthly),
            "projects_count": len(projects),
            "resources_count": len(resources),
            "unsupported_resources_count": unsupported,
            "resources": resources,
            "available": total_monthly is not None or bool(resources),
            "unavailable_reason": None if total_monthly is not None or bool(resources) else "cost data not available",
        }

    def _empty_summary(self, *, unavailable_reason: str) -> dict[str, Any]:
        return {
            "currency": "USD",
            "total_monthly_cost": None,
            "total_hourly_cost": None,
            "past_total_monthly_cost": None,
            "diff_total_monthly_cost": None,
            "projects_count": 0,
            "resources_count": 0,
            "unsupported_resources_count": 0,
            "resources": [],
            "available": False,
            "unavailable_reason": unavailable_reason,
        }

    def _decimal(self, value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    def _string(self, value: Decimal | None) -> str | None:
        return None if value is None else f"{value:.2f}"
