from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .models import Issue


class StateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"running": {}, "retry": {}}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        raw.setdefault("running", {})
        raw.setdefault("retry", {})
        return raw

    def save(self, payload: dict[str, Any]) -> None:
        payload.setdefault("running", {})
        payload.setdefault("retry", {})
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def get_running(self) -> dict[str, dict[str, Any]]:
        return self.load()["running"]

    def get_retry(self) -> dict[str, dict[str, Any]]:
        return self.load()["retry"]

    def get_running_entry(self, issue_id: str) -> dict[str, Any] | None:
        return self.load()["running"].get(issue_id)

    def mark_running(self, issue: Issue) -> None:
        payload = self.load()
        payload["running"][issue.id] = {
            "issue_id": issue.id,
            "issue_identifier": issue.identifier,
            "title": issue.title,
            "state_name": issue.state_name,
            "started_at": time.time(),
            "thread_id": None,
        }
        self.save(payload)

    def update_thread_id(self, issue_id: str, thread_id: str | None) -> None:
        payload = self.load()
        if issue_id in payload["running"]:
            payload["running"][issue_id]["thread_id"] = thread_id
            self.save(payload)

    def clear_running(self, issue_id: str) -> None:
        payload = self.load()
        payload["running"].pop(issue_id, None)
        self.save(payload)

    def set_retry(self, issue: Issue, next_allowed_at: float, attempts: int) -> None:
        payload = self.load()
        payload["retry"][issue.id] = {
            "issue_id": issue.id,
            "issue_identifier": issue.identifier,
            "next_allowed_at": next_allowed_at,
            "attempts": attempts,
        }
        self.save(payload)

    def clear_retry(self, issue_id: str) -> None:
        payload = self.load()
        payload["retry"].pop(issue_id, None)
        self.save(payload)

    def issue_identifier_for(self, issue_id: str) -> str | None:
        payload = self.load()
        for section in ("running", "retry"):
            row = payload[section].get(issue_id)
            if row and row.get("issue_identifier"):
                return str(row["issue_identifier"])
        return None

    def all_known_issue_ids(self) -> set[str]:
        payload = self.load()
        return set(payload["running"]).union(payload["retry"])
