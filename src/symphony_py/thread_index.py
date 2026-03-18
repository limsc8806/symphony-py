from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class ThreadIndexStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"issues": {}, "threads": {}}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        raw.setdefault("issues", {})
        raw.setdefault("threads", {})
        return raw

    def save(self, payload: dict[str, Any]) -> None:
        payload.setdefault("issues", {})
        payload.setdefault("threads", {})
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def upsert_issue_thread(
        self,
        *,
        issue_id: str,
        issue_identifier: str,
        title: str,
        thread_id: str,
        status: str,
        pr_url: str | None,
        archived: bool = False,
        last_operation: str | None = None,
        runtime_status_type: str | None = None,
        runtime_active_flags: list[str] | None = None,
    ) -> None:
        payload = self.load()
        now = time.time()
        prev = payload["threads"].get(thread_id, {})
        first_seen_at = prev.get("first_seen_at", now)
        prev_status_type = prev.get("last_status_type")
        prev_flags = prev.get("last_active_flags", [])
        status_changed_at = prev.get("status_changed_at", now)
        new_flags = runtime_active_flags or prev.get("last_active_flags", [])
        new_status_type = runtime_status_type or prev.get("last_status_type")
        if runtime_status_type is not None:
            if prev_status_type != runtime_status_type or prev_flags != (runtime_active_flags or []):
                status_changed_at = now
        rollback_count = int(prev.get("rollback_count", 0))
        if last_operation == "rollback":
            rollback_count += 1

        record = {
            "issue_id": issue_id,
            "issue_identifier": issue_identifier,
            "title": title,
            "thread_id": thread_id,
            "status": status,
            "pr_url": pr_url,
            "archived": archived,
            "updated_at": now,
            "first_seen_at": first_seen_at,
            "status_changed_at": status_changed_at,
            "last_status_type": new_status_type,
            "last_active_flags": new_flags,
            "watch_started_at": prev.get("watch_started_at"),
            "last_operation": last_operation or prev.get("last_operation"),
            "last_operation_at": now if last_operation else prev.get("last_operation_at"),
            "rollback_count": rollback_count,
        }
        payload["issues"][issue_id] = record | {"thread_id": thread_id}
        payload["threads"][thread_id] = record
        self.save(payload)

    def mark_archived(self, thread_id: str, archived: bool = True) -> None:
        payload = self.load()
        row = payload["threads"].get(thread_id)
        if not row:
            return
        row["archived"] = archived
        row["updated_at"] = time.time()
        issue_id = row.get("issue_id")
        if issue_id in payload["issues"]:
            payload["issues"][issue_id]["archived"] = archived
            payload["issues"][issue_id]["updated_at"] = row["updated_at"]
        self.save(payload)

    def mark_watch_started(self, thread_id: str) -> None:
        payload = self.load()
        row = payload["threads"].get(thread_id)
        if not row:
            return
        ts = time.time()
        row["watch_started_at"] = ts
        row["updated_at"] = ts
        issue_id = row.get("issue_id")
        if issue_id in payload["issues"]:
            payload["issues"][issue_id]["watch_started_at"] = ts
            payload["issues"][issue_id]["updated_at"] = ts
        self.save(payload)

    def clear_watch_started(self, thread_id: str) -> None:
        payload = self.load()
        row = payload["threads"].get(thread_id)
        if not row:
            return
        ts = time.time()
        row["watch_started_at"] = None
        row["updated_at"] = ts
        issue_id = row.get("issue_id")
        if issue_id in payload["issues"]:
            payload["issues"][issue_id]["watch_started_at"] = None
            payload["issues"][issue_id]["updated_at"] = ts
        self.save(payload)

    def get_by_issue_id(self, issue_id: str) -> dict[str, Any] | None:
        return self.load()["issues"].get(issue_id)

    def get_by_thread_id(self, thread_id: str) -> dict[str, Any] | None:
        return self.load()["threads"].get(thread_id)

    def all_issue_entries(self) -> dict[str, dict[str, Any]]:
        return self.load()["issues"]
