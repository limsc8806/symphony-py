from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .activity_log import ActivityLogStore
from .models import Issue, RunResult, WorkflowBundle
from .runtime.codex_runner import CodexRunner
from .runtime.workspace import WorkspaceManager
from .state_store import StateStore
from .thread_index import ThreadIndexStore
from .tracker.linear_client import LinearClient

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetryEntry:
    next_allowed_at: float
    attempts: int = 0


class Orchestrator:
    def __init__(self, workflow: WorkflowBundle, linear: LinearClient) -> None:
        self.workflow = workflow
        self.linear = linear
        self.workspace_manager = WorkspaceManager(workflow.config.workspace.root)
        self.codex_runner = CodexRunner(workflow.config.codex)
        self._running_tasks: dict[str, asyncio.Task[None]] = {}
        self._watchers: dict[str, asyncio.Task[None]] = {}
        self._wake_event = asyncio.Event()
        self._retry: dict[str, RetryEntry] = {}

        state_file = workflow.config.persistence.state_file or str(Path(workflow.config.workspace.root) / "_orchestrator_state.json")
        index_file = workflow.config.thread_catalog.index_file or str(Path(workflow.config.workspace.root) / "_thread_index.json")
        self.state_store = StateStore(state_file)
        self.thread_index = ThreadIndexStore(index_file)
        self.activity_log = ActivityLogStore(Path(workflow.config.workspace.root) / "_activity_log.json")
        self._bootstrapped = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "running_issue_ids": sorted(self._running_tasks.keys()),
            "watching_issue_ids": sorted(self._watchers.keys()),
            "retry": {k: {"next_allowed_at": v.next_allowed_at, "attempts": v.attempts} for k, v in self._retry.items()},
            "persisted_running": self.state_store.get_running(),
            "persisted_retry": self.state_store.get_retry(),
            "thread_index": self.thread_index.all_issue_entries(),
        }

    async def run_forever(self) -> None:
        poll_seconds = self.workflow.config.polling.interval_ms / 1000
        while True:
            try:
                if not self._bootstrapped:
                    self._bootstrap_from_store()
                    self._bootstrapped = True
                await self._tick()
            except Exception:
                logger.exception("orchestrator tick failed")
            try:
                await asyncio.wait_for(self._wake_event.wait(), timeout=poll_seconds)
            except asyncio.TimeoutError:
                pass
            finally:
                self._wake_event.clear()

    def _bootstrap_from_store(self) -> None:
        retry_payload = self.state_store.get_retry()
        for issue_id, item in retry_payload.items():
            self._retry[issue_id] = RetryEntry(next_allowed_at=float(item["next_allowed_at"]), attempts=int(item["attempts"]))

    async def _tick(self) -> None:
        # Left intentionally light for the scaffold.
        return None

    def _extract_runtime_status_from_events(self, events: list[dict[str, Any]] | None) -> tuple[str | None, list[str]]:
        if not events:
            return None, []
        for event in reversed(events):
            if event.get("method") == "thread/status/changed":
                status = event.get("params", {}).get("status", {})
                return status.get("type"), status.get("activeFlags", []) or []
            if event.get("method") == "turn/updated":
                turn = event.get("params", {}).get("turn", {})
                status = turn.get("status")
                if status:
                    return status, []
        return None, []

    async def _finalize(self, issue: Issue, result: RunResult) -> None:
        self.activity_log.append(
            kind="run_result",
            message="issue run finished",
            issue_id=issue.id,
            issue_identifier=issue.identifier,
            thread_id=result.session_id,
            meta={"ok": result.ok, "summary": result.summary, "pr_url": result.pr_url},
        )
        if result.session_id and self.workflow.config.thread_catalog.enabled:
            status_type, active_flags = self._extract_runtime_status_from_events(result.raw_events)
            self.thread_index.upsert_issue_thread(
                issue_id=issue.id,
                issue_identifier=issue.identifier,
                title=issue.title,
                thread_id=result.session_id,
                status="success" if result.ok else "failed",
                pr_url=result.pr_url,
                archived=False,
                last_operation="run",
                runtime_status_type=status_type,
                runtime_active_flags=active_flags,
            )
        if result.ok:
            self.state_store.clear_running(issue.id)
            self.state_store.clear_retry(issue.id)
            self._retry.pop(issue.id, None)
        else:
            await self._schedule_retry(issue)

    async def _schedule_retry(self, issue: Issue) -> None:
        prev = self._retry.get(issue.id)
        attempts = (prev.attempts + 1) if prev else 1
        delay = min(30 * (2 ** (attempts - 1)), self.workflow.config.agent.max_retry_backoff_ms / 1000)
        next_allowed_at = time.time() + delay
        self._retry[issue.id] = RetryEntry(next_allowed_at=next_allowed_at, attempts=attempts)
        self.state_store.set_retry(issue, next_allowed_at=next_allowed_at, attempts=attempts)

    def _set_cooldown(self, issue: Issue, delay_seconds: float) -> None:
        prev = self._retry.get(issue.id)
        attempts = prev.attempts if prev else 0
        next_allowed_at = time.time() + delay_seconds
        self._retry[issue.id] = RetryEntry(next_allowed_at=next_allowed_at, attempts=attempts)
        self.state_store.set_retry(issue, next_allowed_at=next_allowed_at, attempts=attempts)
