from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def sanitize_string(value: str, *, max_length: int = 2048) -> str:
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value).strip()
    return sanitized[:max_length]
