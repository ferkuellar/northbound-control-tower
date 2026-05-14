from __future__ import annotations

import hashlib
from pathlib import Path


class ChecksumService:
    def sha256_file(self, path: Path, *, workspace_root: Path) -> str:
        resolved_path = path.resolve()
        resolved_root = workspace_root.resolve()
        if not resolved_path.is_relative_to(resolved_root):
            raise ValueError("Checksum path must stay inside the Terraform workspace.")
        if not resolved_path.is_file():
            raise FileNotFoundError(f"Checksum file not found: {resolved_path.name}")

        digest = hashlib.sha256()
        with resolved_path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
