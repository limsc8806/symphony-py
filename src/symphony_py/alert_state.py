from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class AlertStateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"acks": {}, "snoozes": {}}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        raw.setdefault("acks", {})
        raw.setdefault("snoozes", {})
        return raw

    def save(self, payload: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def make_key(kind: str, issue_id: str | None, thread_id: str | None) -> str:
        return f"{kind}::{issue_id or '-'}::{thread_id or '-'}"

    def acknowledge(self, *, kind: str, issue_id: str | None, thread_id: str | None, note: str | None = None) -> None:
        payload = self.load()
        key = self.make_key(kind, issue_id, thread_id)
        payload["acks"][key] = {"kind": kind, "issue_id": issue_id, "thread_id": thread_id, "note": note, "acknowledged_at": time.time()}
        self.save(payload)

    def snooze(self, *, kind: str, issue_id: str | None, thread_id: str | None, seconds: int, note: str | None = None) -> None:
        payload = self.load()
        key = self.make_key(kind, issue_id, thread_id)
        now = time.time()
        payload["snoozes"][key] = {"kind": kind, "issue_id": issue_id, "thread_id": thread_id, "note": note, "snoozed_at": now, "until": now + seconds}
        self.save(payload)

    def clear(self, *, kind: str, issue_id: str | None, thread_id: str | None) -> None:
        payload = self.load()
        key = self.make_key(kind, issue_id, thread_id)
        payload["acks"].pop(key, None)
        payload["snoozes"].pop(key, None)
        self.save(payload)

    def get_state(self, *, kind: str, issue_id: str | None, thread_id: str | None) -> dict[str, Any]:
        payload = self.load()
        key = self.make_key(kind, issue_id, thread_id)
        return {"ack": payload["acks"].get(key), "snooze": payload["snoozes"].get(key)}

    def is_suppressed(self, *, kind: str, issue_id: str | None, thread_id: str | None) -> bool:
        payload = self.load()
        key = self.make_key(kind, issue_id, thread_id)
        if key in payload["acks"]:
            return True
        snooze = payload["snoozes"].get(key)
        if not snooze:
            return False
        if float(snooze.get("until", 0)) > time.time():
            return True
        payload["snoozes"].pop(key, None)
        self.save(payload)
        return False
