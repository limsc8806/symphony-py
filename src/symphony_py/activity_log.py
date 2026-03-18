from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class ActivityLogStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, rows: list[dict[str, Any]]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def append(self, *, kind: str, message: str, issue_id: str | None = None,
               issue_identifier: str | None = None, thread_id: str | None = None,
               meta: dict[str, Any] | None = None) -> None:
        rows = self._load()
        rows.append({
            "ts": time.time(),
            "kind": kind,
            "message": message,
            "issue_id": issue_id,
            "issue_identifier": issue_identifier,
            "thread_id": thread_id,
            "meta": meta or {},
        })
        self._save(rows[-1000:])

    def list_all(self, limit: int = 200) -> list[dict[str, Any]]:
        return list(reversed(self._load()))[:limit]

    def list_for_thread(self, thread_id: str, limit: int = 200) -> list[dict[str, Any]]:
        return [x for x in self.list_all(limit=1000) if x.get("thread_id") == thread_id][:limit]
