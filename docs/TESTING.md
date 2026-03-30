# Testing Guide

이 문서는 `symphony-py` 프로젝트의 테스트 전략과 실행 방법을 설명합니다.

이 프로젝트는 일반 애플리케이션과 달리 **오케스트레이터 / 운영 시스템**이기 때문에 다음을 검증하는 것이 중요합니다.

- orchestrator 상태 관리
- retry / backoff 로직
- thread catalog
- alert state
- admin API
- workflow parsing

---

# 1. 테스트 구조


tests/
├─ test_alert_state_store.py
├─ test_alert_recommendations.py
├─ test_ops_alerts_time_based.py
├─ test_dashboard_html_contains_toast_and_actions.py
└─ ...


테스트는 크게 다음 영역으로 나뉩니다.

## Unit Tests

대상:

- state store
- alert state
- thread index
- workflow loader
- dispatch rules

목표:

- 로직 정확성 검증
- edge case 검증

예:


tests/test_alert_state_store.py


---

## API Tests

대상:

- FastAPI ops endpoints

예:


/health
/state
/alerts
/issues
/threads
/admin/*


FastAPI `TestClient`로 테스트합니다.

---

## Dashboard HTML Tests

대상:

- dashboard HTML output
- 주요 UI element 존재 여부

예:

- toastRoot
- runRecommendedAction
- alert banners

---

# 2. 테스트 실행

## 전체 테스트


pytest -q


---

## 특정 테스트


pytest tests/test_alert_state_store.py


---

## verbose 모드


pytest -vv


---

# 3. 코드 품질 검사

## Ruff (lint)


ruff check .


---

## mypy (type check)


mypy src


---

# 4. CI 권장 설정

GitHub Actions 예시


jobs:
test:
runs-on: ubuntu-latest

steps:
  - uses: actions/checkout@v4

  - uses: actions/setup-python@v5
    with:
      python-version: "3.11"

  - run: pip install -e ".[dev]"
  - run: pytest -q
  - run: ruff check .
  - run: mypy src

---

# 5. 테스트 작성 규칙

테스트는 다음 원칙을 따릅니다.

### 1. deterministic

외부 API 호출 없이 동작해야 합니다.

예:

- Linear API → mock
- Codex runner → mock

---

### 2. filesystem isolation

`tmp_path` 사용

예:


ThreadIndexStore(tmp_path / "thread_index.json")


---

### 3. 최소 의존성

가능한 작은 fixture 사용.

---

# 6. 운영 로직 테스트 전략

이 프로젝트는 **오케스트레이터**이므로 다음을 특히 검증해야 합니다.

### retry


retry attempts 증가
backoff 적용


### watcher


waitingOnApproval 상태
watcher 시작
watcher 종료


### alerting


time based alerts
retry hotspot
long active thread


---

# 7. 수동 테스트

dashboard 테스트:


symphony-py serve-ops --workflow WORKFLOW.md


접속:


http://127.0.0.1:8080/dashboard


확인 항목:

- alerts 표시
- recommended actions
- compact / rollback
- ack / snooze
- activity feed

---

# 8. 실패 분석

테스트 실패 시 확인 순서:

1. state store 파일
2. workflow 설정
3. retry 로직
4. alert suppression
5. thread catalog

---

# 9. 테스트 작성 권장 패턴


def test_alert_detection(tmp_path):
idx = ThreadIndexStore(tmp_path / "thread_index.json")

idx.upsert_issue_thread(...)

result = compute_alerts()

assert result[0]["kind"] == "waiting_on_approval"

---

# 10. 장기 목표

향후 추가 테스트:

- orchestrator integration test
- codex runner mock server
- workflow validation fuzz tests