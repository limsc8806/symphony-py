from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class TrackerConfig(BaseModel):
    kind: Literal["linear"]
    project_slug: str
    api_key: str


class PollingConfig(BaseModel):
    interval_ms: int = Field(default=30_000, ge=1_000)


class IssueStatesConfig(BaseModel):
    active_states: list[str]
    terminal_states: list[str]


class WorkspaceConfig(BaseModel):
    root: str


class HooksConfig(BaseModel):
    after_create: str | None = None
    before_run: str | None = None
    after_run: str | None = None
    before_remove: str | None = None
    timeout_ms: int = Field(default=60_000, ge=1_000)


class AgentConfig(BaseModel):
    max_concurrent_agents: int = Field(default=1, ge=1)
    max_concurrent_agents_by_state: dict[str, int] = Field(default_factory=dict)
    max_turns: int = Field(default=12, ge=1)
    max_retry_backoff_ms: int = Field(default=300_000, ge=1_000)


class DispatchConfig(BaseModel):
    required_labels_any: list[str] = Field(default_factory=lambda: ["safe"])
    forbidden_labels_any: list[str] = Field(default_factory=list)


class PersistenceConfig(BaseModel):
    enabled: bool = True
    state_file: str | None = None
    archive_root: str | None = None


class PreflightCommand(BaseModel):
    argv: list[str]
    timeout_ms: int = Field(default=10_000, ge=1_000)
    required_exit_code: int = 0
    enabled: bool = True


class PreflightConfig(BaseModel):
    enabled: bool = True
    commands: list[PreflightCommand] = Field(default_factory=list)


class ResumeConfig(BaseModel):
    enabled: bool = True
    active_thread_policy: Literal["skip", "steer"] = "skip"
    steer_prompt: str = "Continue the current task and summarize blockers clearly."
    skip_active_flags_any: list[str] = Field(default_factory=lambda: ["waitingOnApproval"])


class WatcherConfig(BaseModel):
    enabled: bool = True
    timeout_ms: int = Field(default=900_000, ge=5_000)
    cooldown_while_watching_seconds: int = Field(default=300, ge=1)


class ThreadCatalogConfig(BaseModel):
    enabled: bool = True
    index_file: str | None = None
    archive_on_inactive_cleanup: bool = True
    archive_on_success: bool = False
    list_page_size: int = Field(default=50, ge=1, le=200)


class AlertingConfig(BaseModel):
    enabled: bool = True
    waiting_on_approval_warn_after_seconds: int = 300
    waiting_on_approval_bad_after_seconds: int = 1800
    watcher_warn_after_seconds: int = 300
    watcher_bad_after_seconds: int = 1800
    active_thread_warn_after_seconds: int = 900
    active_thread_bad_after_seconds: int = 3600
    retry_warn_attempts: int = 3
    retry_bad_attempts: int = 5


class AlertStateConfig(BaseModel):
    enabled: bool = True
    state_file: str | None = None
    default_snooze_seconds: int = 1800


class AdminApiConfig(BaseModel):
    enabled: bool = True
    token: str | None = None
    bind_host: str = "127.0.0.1"
    port: int = 8080


class CodexConfig(BaseModel):
    command: str = "codex app-server"
    model: str = "gpt-5.4"
    approval_policy: str = "unlessTrusted"
    thread_sandbox: str = "workspaceWrite"
    effort: str = "medium"
    summary: str = "concise"
    experimental_api: bool = False
    opt_out_notification_methods: list[str] = Field(default_factory=list)
    auto_approve_commands: bool = False
    auto_approve_file_changes: bool = False
    approval_decision: str = "decline"
    stall_timeout_ms: int = Field(default=900_000, ge=5_000)


class ServerConfig(BaseModel):
    port: int = Field(default=8080, ge=1, le=65535)


class WorkflowConfig(BaseModel):
    tracker: TrackerConfig
    polling: PollingConfig = Field(default_factory=PollingConfig)
    issue_states: IssueStatesConfig
    workspace: WorkspaceConfig
    hooks: HooksConfig = Field(default_factory=HooksConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    dispatch: DispatchConfig = Field(default_factory=DispatchConfig)
    persistence: PersistenceConfig = Field(default_factory=PersistenceConfig)
    preflight: PreflightConfig = Field(default_factory=PreflightConfig)
    resume: ResumeConfig = Field(default_factory=ResumeConfig)
    watcher: WatcherConfig = Field(default_factory=WatcherConfig)
    thread_catalog: ThreadCatalogConfig = Field(default_factory=ThreadCatalogConfig)
    alerting: AlertingConfig = Field(default_factory=AlertingConfig)
    alert_state: AlertStateConfig = Field(default_factory=AlertStateConfig)
    admin_api: AdminApiConfig = Field(default_factory=AdminApiConfig)
    codex: CodexConfig = Field(default_factory=CodexConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)


@dataclass(slots=True)
class WorkflowBundle:
    config: WorkflowConfig
    prompt: str
    source_path: Path


@dataclass(slots=True)
class Issue:
    id: str
    identifier: str
    title: str
    description: str
    priority: int
    state_name: str
    state_type: str | None
    labels: list[str]
    url: str | None = None


@dataclass(slots=True)
class RunResult:
    ok: bool
    summary: str
    session_id: str | None = None
    pr_url: str | None = None
    raw_events: list[dict[str, Any]] | None = None
