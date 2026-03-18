from fastapi.testclient import TestClient

from symphony_py.api.app import build_api
from symphony_py.models import CodexConfig, WorkflowConfig


class DummyOrchestrator:
    workflow = type("W", (), {"config": WorkflowConfig.model_validate({
        "tracker": {"kind": "linear", "project_slug": "p", "api_key": "k"},
        "issue_states": {"active_states": ["Todo"], "terminal_states": ["Done"]},
        "workspace": {"root": "."}
    })})()
    _retry = {}
    _wake_event = type("Wake", (), {"set": lambda self: None})()

    def snapshot(self):
        return {"running_issue_ids": [], "watching_issue_ids": [], "retry": {}, "persisted_running": {}, "persisted_retry": {}, "thread_index": {}}


def test_admin_ack_and_snooze_routes(tmp_path):
    app = build_api(orchestrator=DummyOrchestrator(), workspace_root=str(tmp_path), thread_index_file=str(tmp_path / "thread_index.json"), codex_config=CodexConfig(), admin_token="secret")
    client = TestClient(app)
    res = client.post("/admin/alerts/ack?kind=waiting_on_approval&issue_id=issue-1&thread_id=thread-1", headers={"x-admin-token": "secret"})
    assert res.status_code == 200
    res = client.post("/admin/alerts/snooze?kind=waiting_on_approval&issue_id=issue-1&thread_id=thread-1&seconds=60", headers={"x-admin-token": "secret"})
    assert res.status_code == 200
