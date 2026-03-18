---
tracker:
  kind: linear
  project_slug: "example-project"
  api_key: $LINEAR_API_KEY

polling:
  interval_ms: 30000

issue_states:
  active_states:
    - Todo
    - Autonomous
    - Changes Requested
  terminal_states:
    - Done
    - Closed

workspace:
  root: ./.symphony/workspaces

hooks:
  timeout_ms: 60000

agent:
  max_concurrent_agents: 1
  max_turns: 12
  max_retry_backoff_ms: 300000

dispatch:
  required_labels_any: ["safe"]
  forbidden_labels_any: ["blocked", "requires-human"]

persistence:
  enabled: true
  state_file: ./.symphony/orchestrator_state.json
  archive_root: ./.symphony/archive

preflight:
  enabled: true
  commands:
    - argv: ["python", "--version"]
      timeout_ms: 5000
      required_exit_code: 0

resume:
  enabled: true
  active_thread_policy: "skip"
  steer_prompt: "Continue the current task and summarize blockers clearly."
  skip_active_flags_any: ["waitingOnApproval"]

watcher:
  enabled: true
  timeout_ms: 900000
  cooldown_while_watching_seconds: 300

thread_catalog:
  enabled: true
  index_file: ./.symphony/thread_index.json
  archive_on_inactive_cleanup: true
  archive_on_success: false
  list_page_size: 50

alerting:
  enabled: true
  waiting_on_approval_warn_after_seconds: 300
  waiting_on_approval_bad_after_seconds: 1800
  watcher_warn_after_seconds: 300
  watcher_bad_after_seconds: 1800
  active_thread_warn_after_seconds: 900
  active_thread_bad_after_seconds: 3600
  retry_warn_attempts: 3
  retry_bad_attempts: 5

alert_state:
  enabled: true
  state_file: ./.symphony/alert_state.json
  default_snooze_seconds: 1800

admin_api:
  enabled: true
  token: $SYMPHONY_ADMIN_TOKEN
  bind_host: "127.0.0.1"
  port: 8080

codex:
  command: "codex app-server"
  model: "gpt-5.4"
  approval_policy: "unlessTrusted"
  thread_sandbox: "workspaceWrite"
  effort: "medium"
  summary: "concise"
  stall_timeout_ms: 900000

server:
  port: 8080
---
You are the implementation agent.
- Read AGENTS.md and docs/ first.
- Prefer the smallest safe fix.
- Record validation clearly.
