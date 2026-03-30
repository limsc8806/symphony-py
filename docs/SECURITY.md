# Security Policy

`symphony-py`는 **자율 개발 오케스트레이터**이므로 보안이 중요합니다.

이 문서는 운영 시 따라야 할 보안 정책을 설명합니다.

---

# 1. 위협 모델

이 시스템은 다음 권한을 가질 수 있습니다.

- 코드 수정
- 테스트 실행
- Git commit
- workspace 파일 변경
- external API 호출

따라서 **잘못된 자동 실행은 위험할 수 있습니다.**

---

# 2. 기본 보안 원칙

### 최소 권한

- workspace sandbox 사용
- production repo 직접 변경 금지

---

### 승인 정책

Codex App Server 설정:


approval_policy: unlessTrusted


또는


approval_policy: always


---

### dispatch 제한

자동 실행 이슈는 반드시 라벨로 제한합니다.

예:


required_labels_any:

safe

---

# 3. Admin API 보호

Admin API는 반드시 다음을 만족해야 합니다.

### token required


SYMPHONY_ADMIN_TOKEN


---

### 내부망 바인딩


127.0.0.1


또는


private network only


---

### reverse proxy

운영 환경에서는 다음을 권장합니다.


nginx
cloudflare tunnel
internal VPN


---

# 4. 위험한 작업

다음 작업은 자동 실행하면 안 됩니다.

- database migration
- infrastructure changes
- secrets modification
- deployment pipelines

---

# 5. sandbox 정책

권장 설정


thread_sandbox: workspaceWrite


피해야 할 설정


dangerouslySkipSandbox


---

# 6. secrets 관리

다음 값은 절대 코드에 넣지 않습니다.


LINEAR_API_KEY
SYMPHONY_ADMIN_TOKEN
GITHUB_TOKEN


환경 변수로 설정합니다.

---

# 7. audit log

운영 중 반드시 기록해야 합니다.

- admin actions
- thread rollback
- compact operations
- alert suppression

이 로그는 `activity_log.json`에 기록됩니다.

---

# 8. alert system

alert는 보안 이벤트를 탐지하는 데도 사용됩니다.

예:

- retry hotspot
- long active thread
- unexpected failure

운영자는 반드시 확인해야 합니다.

---

# 9. 운영 체크리스트

배포 전 확인:


✓ admin token 설정
✓ dispatch rules 확인
✓ safe label 적용
✓ sandbox mode 확인
✓ alerting 활성화
✓ activity log 기록 확인


---

# 10. 취약점 보고

보안 문제 발견 시 다음 정보를 포함해 보고합니다.

- 재현 방법
- 영향 범위
- 예상 위험도
- 완화 방법

---

# 11. 향후 보안 개선

예정 기능:

- RBAC admin API
- audit export
- signed actions
- workflow policy validation
추천 저장소 구조

지금 저장소는 다음처럼 되는 것이 가장 좋습니다.

symphony-py
│
├─ README.md
├─ WORKFLOW.md
├─ AGENTS.md
│
├─ docs
│   ├─ TESTING.md
│   └─ SECURITY.md
│
├─ src
├─ tests
└─ pyproject.toml