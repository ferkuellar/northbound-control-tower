from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TerraformPlanParser:
    def parse_file(self, path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("Terraform plan JSON is invalid or unreadable.") from exc
        return self.parse(payload)

    def parse(self, payload: dict[str, Any]) -> dict[str, Any]:
        counts = {
            "add": 0,
            "change": 0,
            "delete": 0,
            "replace": 0,
            "no_op": 0,
        }
        providers: set[str] = set()
        resource_changes = payload.get("resource_changes") or []
        for change in resource_changes:
            provider = change.get("provider_name")
            if provider:
                providers.add(str(provider))
            actions = set((change.get("change") or {}).get("actions") or [])
            if actions == {"no-op"}:
                counts["no_op"] += 1
            elif "delete" in actions and "create" in actions:
                counts["replace"] += 1
            elif "delete" in actions:
                counts["delete"] += 1
            elif "update" in actions:
                counts["change"] += 1
            elif "create" in actions:
                counts["add"] += 1

        return {
            "resource_changes_count": len(resource_changes),
            "add_count": counts["add"],
            "change_count": counts["change"],
            "delete_count": counts["delete"],
            "replace_count": counts["replace"],
            "no_op_count": counts["no_op"],
            "providers_used": sorted(providers),
            "terraform_version": payload.get("terraform_version"),
            "has_destructive_changes": counts["delete"] > 0 or counts["replace"] > 0,
            "raw_counts": counts,
        }
