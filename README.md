# symphony-py

A Python orchestration layer for Codex App Server with:
- workflow loading from `WORKFLOW.md`
- issue/thread catalog
- alert acknowledgement and snoozing
- simple ops dashboard and admin actions

## Quick start

```bash
pip install -e ".[dev]"
symphony-py validate --workflow WORKFLOW.md
symphony-py serve-ops --workflow WORKFLOW.md --host 127.0.0.1 --port 8080
```
