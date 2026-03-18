# symphony-py

`symphony-py`는 **Codex App Server 기반 자율개발 오케스트레이터**입니다.  
이 프로젝트는 이슈 트래커(현재 Linear)를 폴링해서 작업 가능한 이슈를 고르고, 이슈별 workspace를 준비한 뒤, Codex App Server에 thread를 시작하거나 재개해서 구현 작업을 수행하도록 설계되어 있습니다.

또한 단순 실행기 수준이 아니라, 운영을 위한 다음 기능을 포함합니다.

- `WORKFLOW.md` 기반 설정/프롬프트 로딩
- Linear 이슈 조회/상태 전이/코멘트
- 이슈별 workspace 관리
- retry / backoff / state persistence
- thread catalog 및 issue ↔ thread 매핑
- alerting / acknowledgement / snooze
- 운영용 FastAPI dashboard / admin actions
- thread archive / unarchive / compact / rollback 연계

---

## 1. 프로젝트 목적

이 프로젝트의 목적은 다음과 같습니다.

1. 사람이 직접 매번 코딩 에이전트를 붙잡고 있지 않아도 되도록 한다.
2. 이슈를 기준으로 안전하게 자동 실행한다.
3. 실패, 재시도, approval 대기, 장시간 active thread 같은 운영 문제를 추적한다.
4. 운영자가 dashboard에서 현재 상태를 확인하고 필요한 관리 액션을 직접 실행할 수 있게 한다.

즉, `symphony-py`는 “코드 생성기”가 아니라 **자율개발 시스템의 운영 계층**입니다.

---

## 2. 핵심 구성 요소

### Orchestrator
오케스트레이터는 다음을 담당합니다.

- active issue polling
- dispatch policy 적용
- retry/backoff
- watcher lifecycle
- persisted state 복구
- preflight 실행
- thread resume / steer / compact / rollback 정책 적용

### Codex Runner
Codex Runner는 Codex App Server와의 통신을 담당합니다.

- `initialize` / `initialized`
- `thread/start`
- `thread/resume`
- `thread/read`
- `turn/start`
- `turn/steer`
- `thread/list`
- `thread/loaded/list`
- `thread/archive`
- `thread/unarchive`
- `thread/compact/start`
- `thread/rollback`
- `command/exec`

### State / Index / Alert Stores
로컬 JSON 기반 저장소를 사용합니다.

- orchestrator state: running / retry 상태
- thread index: issue ↔ thread 매핑, 운영 메타데이터
- activity log: 운영 액션 및 실행 이력
- alert state: acknowledge / snooze 상태

### Ops API / Dashboard
FastAPI 기반 운영 UI를 제공합니다.

- health
- current orchestrator state
- issues / threads / thread detail
- activity feed
- alerts
- admin actions

---

## 3. 디렉터리 구조

```text
symphony-py/
├── src/symphony_py/
│   ├── api/
│   ├── runtime/
│   ├── tracker/
│   ├── orchestrator.py
│   ├── workflow_loader.py
│   ├── models.py
│   ├── state_store.py
│   ├── thread_index.py
│   ├── activity_log.py
│   ├── alert_state.py
│   └── main.py
├── tests/
├── README.md
├── WORKFLOW.md
├── AGENTS.md
└── pyproject.toml