import textwrap

from symphony_py.workflow_loader import load_workflow


def test_load_workflow_parses_front_matter_and_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "test-linear-key")
    workflow_file = tmp_path / "WORKFLOW.md"
    workflow_file.write_text(textwrap.dedent("""\
    ---
    tracker:
      kind: linear
      project_slug: "core-platform"
      api_key: $LINEAR_API_KEY
    issue_states:
      active_states: [Todo]
      terminal_states: [Done]
    workspace:
      root: ./w
    ---
    hello
    """), encoding="utf-8")
    bundle = load_workflow(workflow_file)
    assert bundle.config.tracker.api_key == "test-linear-key"
    assert bundle.prompt == "hello"
