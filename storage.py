"""Validated, atomic JSON file storage for a single-computer classroom prototype."""
from __future__ import annotations
import copy
import json
import os
import tempfile
from pathlib import Path


class StorageError(ValueError):
    pass


DEFAULT = {
    "schema_version": 1, "active_period": "2026-2027 / 1st Semester",
    "users": [], "students": [], "departments": [], "events": [],
    "attendance": [], "approvals": [], "audit": [],
}


class JsonStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict:
        if not self.path.exists():
            return copy.deepcopy(DEFAULT)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema_version") != 1:
                raise ValueError("Unsupported or invalid data format")
            for name in ("users", "students", "departments", "events", "attendance", "approvals", "audit"):
                if not isinstance(data.get(name), list):
                    raise ValueError(f"Invalid data section: {name}")
            if not isinstance(data.get("active_period"), str):
                raise ValueError("Invalid clearance period")
            return data
        except (OSError, ValueError, UnicodeError) as exc:
            raise StorageError(f"Cannot load {self.path.name}: {exc}") from exc

    def save(self, data: dict) -> None:
        """Save atomically; do not overwrite a previously saved file with malformed content."""
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise StorageError("Invalid data for saving")
        temp_path = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent,
                                             prefix=".clearance-", suffix=".tmp", delete=False) as f:
                temp_path = Path(f.name)
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.path)
        except (OSError, TypeError, ValueError) as exc:
            raise StorageError(f"Cannot save {self.path.name}: {exc}") from exc
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
