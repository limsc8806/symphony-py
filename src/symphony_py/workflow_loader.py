from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from .models import WorkflowBundle, WorkflowConfig

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(?P<yaml>.*?)\n---\s*\n?(?P<body>.*)\Z", re.DOTALL)


class WorkflowLoadError(ValueError):
    pass


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    return value


def load_workflow(path: str | Path) -> WorkflowBundle:
    workflow_path = Path(path).resolve()
    raw = workflow_path.read_text(encoding="utf-8")
    match = _FRONT_MATTER_RE.match(raw)
    if not match:
        raise WorkflowLoadError("WORKFLOW.md must contain YAML front matter between --- markers.")
    yaml_text = match.group("yaml")
    body = match.group("body").strip()
    try:
        config_dict = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        raise WorkflowLoadError(f"Invalid YAML front matter: {exc}") from exc
    config = WorkflowConfig.model_validate(_expand_env(config_dict))
    if not body:
        raise WorkflowLoadError("WORKFLOW.md prompt body is empty.")
    return WorkflowBundle(config=config, prompt=body, source_path=workflow_path)
