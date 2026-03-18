from symphony_py.api.app import _recommended_actions


def test_recommended_actions_for_waiting_on_approval():
    actions = _recommended_actions({"kind": "waiting_on_approval", "issue_id": "issue-1", "thread_id": "thread-1", "level": "warn"})
    names = [a["action"] for a in actions]
    assert "ack" in names and "snooze_600" in names and "detail" in names


def test_recommended_actions_for_failed_thread():
    actions = _recommended_actions({"kind": "failed_thread", "issue_id": "issue-1", "thread_id": "thread-1", "level": "bad"})
    names = [a["action"] for a in actions]
    assert "rollback_1" in names and "compact" in names and "archive" in names
