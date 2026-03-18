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
        return {"running_issue_ids": ["issue-1"], "watching_issue_ids": [], "retry": {}, "persisted_running": {}, "persisted_retry": {}, "thread_index": {}}


def test_health_route(tmp_path):
    app = build_api(orchestrator=DummyOrchestrator(), workspace_root=str(tmp_path), thread_index_file=str(tmp_path / "thread_index.json"), codex_config=CodexConfig(), admin_token="secret")
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_dashboard_route(tmp_path):
    app = build_api(orchestrator=DummyOrchestrator(), workspace_root=str(tmp_path), thread_index_file=str(tmp_path / "thread_index.json"), codex_config=CodexConfig(), admin_token="secret")
    client = TestClient(app)
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "symphony-py ops" in res.text
