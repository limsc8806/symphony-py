from symphony_py.thread_index import ThreadIndexStore


def test_thread_index_watch_started_roundtrip(tmp_path):
    idx = ThreadIndexStore(tmp_path / "thread_index.json")
    idx.upsert_issue_thread(issue_id="issue-1", issue_identifier="CORE-1", title="Watch", thread_id="thread-123", status="success", pr_url=None, archived=False)
    idx.mark_watch_started("thread-123")
    row = idx.get_by_thread_id("thread-123")
    assert row and row["watch_started_at"] is not None
    idx.clear_watch_started("thread-123")
    row = idx.get_by_thread_id("thread-123")
    assert row and row["watch_started_at"] is None
