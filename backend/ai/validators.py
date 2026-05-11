from __future__ import annotations

import json
import re
from typing import Any

from ai.errors import AIOutputValidationError

CREDENTIAL_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bASIA[0-9A-Z]{16}\b"),
    re.compile(r"Bearer\s+eyJ", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]
EXECUTED_ACTION_PATTERNS = [
    re.compile(r"\bI (deleted|terminated|modified|remediated|created|executed)\b", re.IGNORECASE),
    re.compile(r"\bhas been (deleted|terminated|modified|remediated|created)\b", re.IGNORECASE),
]
DESTRUCTIVE_WORDS = ("delete", "terminate", "destroy", "remove")
SAFETY_WORDS = ("approval", "backup", "snapshot", "rollback", "validate")


def parse_ai_output(raw_text: str) -> dict[str, Any]:
    stripped = raw_text.strip()
    if not stripped:
        raise AIOutputValidationError("AI provider returned an empty response")
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return {"analysis_text": raw_text}


def validate_ai_output(raw_text: str, *, context: dict[str, Any]) -> dict[str, Any]:
    for pattern in CREDENTIAL_PATTERNS:
        if pattern.search(raw_text):
            raise AIOutputValidationError("AI output appears to contain credential material")
    for pattern in EXECUTED_ACTION_PATTERNS:
        if pattern.search(raw_text):
            raise AIOutputValidationError("AI output claims an action was executed")

    lowered = raw_text.lower()
    if any(word in lowered for word in DESTRUCTIVE_WORDS) and not any(word in lowered for word in SAFETY_WORDS):
        raise AIOutputValidationError("AI output includes destructive recommendations without safety validation language")

    allowed_providers = set(context.get("inventory_summary", {}).get("by_provider", {}).keys())
    scope_provider = context.get("scope", {}).get("provider")
    if scope_provider and scope_provider != "all":
        allowed_providers.add(str(scope_provider))
    for provider in ("aws", "oci", "azure", "gcp"):
        if provider in lowered and provider not in allowed_providers and provider not in {"aws", "oci"}:
            raise AIOutputValidationError(f"AI output references unsupported provider: {provider}")

    output = parse_ai_output(raw_text)
    if not context.get("limitations", {}).get("resources_available") and "limitation" not in lowered:
        raise AIOutputValidationError("AI output must state limitations when resource context is missing")
    return output
