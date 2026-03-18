from symphony_py.alert_state import AlertStateStore


def test_ack_snooze_and_clear(tmp_path):
    store = AlertStateStore(tmp_path / "alert_state.json")
    store.acknowledge(kind="waiting_on_approval", issue_id="issue-1", thread_id="thread-1", note="looking")
    state = store.get_state(kind="waiting_on_approval", issue_id="issue-1", thread_id="thread-1")
    assert state["ack"] is not None
    assert store.is_suppressed(kind="waiting_on_approval", issue_id="issue-1", thread_id="thread-1") is True
    store.clear(kind="waiting_on_approval", issue_id="issue-1", thread_id="thread-1")
    state = store.get_state(kind="waiting_on_approval", issue_id="issue-1", thread_id="thread-1")
    assert state["ack"] is None
    store.snooze(kind="waiting_on_approval", issue_id="issue-1", thread_id="thread-1", seconds=60)
    assert store.is_suppressed(kind="waiting_on_approval", issue_id="issue-1", thread_id="thread-1") is True
