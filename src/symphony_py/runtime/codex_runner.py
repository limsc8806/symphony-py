from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import CodexConfig, Issue, RunResult


class CodexRunner:
    """A thin, mostly mocked integration boundary.

    This project zip is intended as a working scaffold. Real App Server JSONL integration can be
    added behind these methods without changing the surrounding architecture.
    """

    def __init__(self, config: CodexConfig) -> None:
        self.config = config

    async def inspect_thread(self, workspace: Path, thread_id: str, include_turns: bool = True) -> dict[str, Any]:
        thread = {
            "id": thread_id,
            "name": f"Thread {thread_id}",
            "status": {"type": "idle", "activeFlags": []},
            "turns": [],
        }
        if include_turns:
            thread["turns"] = [{"id": f"{thread_id}-turn-1", "status": "completed", "summary": "stub turn"}]
        return thread

    async def list_threads(
        self,
        workspace: Path,
        *,
        cursor: str | None = None,
        limit: int = 50,
        archived: bool | None = None,
        cwd_filter: str | None = None,
        sort_key: str = "updated_at",
    ) -> dict[str, Any]:
        items = [{
            "id": "thread-123",
            "name": "Main thread",
            "preview": "Fix tests",
            "updatedAt": 1730832222,
            "status": {"type": "idle", "activeFlags": []},
            "cwd": cwd_filter or str(workspace),
        }]
        if archived is True:
            items = []
        return {"data": items[:limit], "nextCursor": None}

    async def list_loaded_threads(self, workspace: Path) -> list[str]:
        return ["thread-123"]

    async def archive_thread(self, workspace: Path, thread_id: str) -> None:
        return None

    async def unarchive_thread(self, workspace: Path, thread_id: str) -> dict[str, Any]:
        return {"id": thread_id, "name": "Restored thread"}

    async def compact_thread(self, workspace: Path, thread_id: str) -> None:
        return None

    async def rollback_thread(self, workspace: Path, thread_id: str, turns: int = 1) -> dict[str, Any]:
        return {"id": thread_id, "rolledBackTurns": turns}

    async def run_issue(self, issue: Issue, workspace: Path, prompt: str, max_turns: int, resume_thread_id: str | None = None) -> RunResult:
        thread_id = resume_thread_id or f"thread-{issue.identifier}"
        events = [{"method": "turn/updated", "params": {"turn": {"status": "completed"}}}]
        return RunResult(ok=True, summary="stub execution completed", session_id=thread_id, pr_url=None, raw_events=events)
