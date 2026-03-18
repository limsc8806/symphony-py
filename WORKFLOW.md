
## `WORKFLOW.md`

```md
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
  required_labels_any:
    - safe
  forbidden_labels_any:
    - blocked
    - requires-human

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
  skip_active_flags_any:
    - waitingOnApproval

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

# Symphony Workflow Contract

이 파일은 `symphony-py`가 읽는 **실행 정책 + agent prompt**입니다.  
YAML front matter는 오케스트레이터 설정이고, 아래 Markdown 본문은 Codex App Server에 전달할 작업 지침입니다.

## 설정 설명

### tracker
이슈 소스를 정의합니다.

- `kind`: 현재는 `linear`
- `project_slug`: 감시할 Linear 프로젝트 slug
- `api_key`: Linear API key

### polling
이슈 폴링 주기입니다.

- `interval_ms`: active issue를 다시 읽는 간격

### issue_states
자동 실행 대상과 종료 상태를 정의합니다.

- `active_states`: 현재 작업 대상으로 볼 상태
- `terminal_states`: cleanup 대상으로 볼 종료 상태

### workspace
이슈별 workspace 루트 경로입니다.

### hooks
workspace lifecycle 훅입니다.

현재 최소 설정은 `timeout_ms`만 있지만, 필요하면 다음을 추가할 수 있습니다.

- `after_create`
- `before_run`
- `after_run`
- `before_remove`

### agent
오케스트레이터 레벨 제한입니다.

- 동시 실행 수
- turn 상한
- retry backoff 상한

### dispatch
어떤 이슈를 자동 실행할지 결정합니다.

예시:
- `safe` 라벨이 있어야 함
- `blocked`, `requires-human`이 있으면 제외

### persistence
오케스트레이터 상태 파일 위치입니다.

- running
- retry
- archive root

### preflight
turn 시작 전에 빠르게 실행할 단일 명령들입니다.

권장:
- 짧고 결정적인 명령만 사용
- 전체 테스트 실행은 여기보다 실제 작업 단계에서 수행

### resume
저장된 thread를 어떻게 재개할지 정합니다.

- `active_thread_policy: skip | steer`
- `skip_active_flags_any`: 이 flag가 있으면 새 turn을 바로 시작하지 않음

기본 예시의 `waitingOnApproval`은 대표적인 skip 대상입니다.

### watcher
approval 대기 같은 상태를 감시하는 watcher 정책입니다.

### thread_catalog
issue ↔ thread 매핑 저장 정책입니다.

### alerting
시간 기반 경고 기준입니다.

예:
- approval 대기 5분 이상 → warn
- approval 대기 30분 이상 → bad
- retry 3회 이상 → warn
- retry 5회 이상 → bad

### alert_state
운영자가 ack / snooze 한 경고 상태 저장 파일입니다.

### admin_api
운영 대시보드와 관리자 액션 API 설정입니다.

반드시:
- 내부망 bind
- admin token 설정

### codex
Codex App Server 연결 설정입니다.

- `command`
- `model`
- `approval_policy`
- `thread_sandbox`
- `effort`
- `summary`
- `stall_timeout_ms`

### server
내부 API 서버 포트입니다.

---

# Agent Prompt

You are the implementation agent.

## Your job
- Read the repository instructions first.
- Understand the issue before changing code.
- Prefer the smallest safe change.
- Validate clearly.
- Report blockers honestly.

## Mandatory rules
- Read `AGENTS.md` and repository docs first.
- Do not guess.
- If the task is ambiguous, make the smallest safe interpretation and record assumptions.
- If you could not run validation, say exactly why.
- Do not hide failing checks.
- Do not expand scope unnecessarily.

## Validation rules
- Run available validation commands when possible.
- Summarize:
  - what changed
  - why it changed
  - what was validated
  - remaining risks
  - blockers, if any

## Safety rules
Do not auto-merge or silently finalize risky changes involving:
- auth
- security
- payments
- destructive data operations
- infrastructure or deployment
- schema-changing operations

## Output expectations
When you finish, produce a result that helps the orchestrator and reviewer understand:
- implementation summary
- validation summary
- failure reason or blocker, if applicable
- whether human follow-up is needed