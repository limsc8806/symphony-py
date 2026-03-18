from __future__ import annotations

import re
import shutil
import tarfile
from pathlib import Path


def sanitize_issue_identifier(identifier: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", identifier.strip())
    return safe.strip("-") or "unknown-issue"


class WorkspaceManager:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for_issue(self, issue_identifier: str) -> Path:
        path = (self.root / sanitize_issue_identifier(issue_identifier)).resolve()
        path.relative_to(self.root)
        return path

    def ensure(self, issue_identifier: str) -> Path:
        path = self.path_for_issue(issue_identifier)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def archive_and_remove(self, issue_identifier: str, archive_root: str | Path) -> Path:
        workspace = self.path_for_issue(issue_identifier)
        archive_dir = Path(archive_root).expanduser().resolve()
        archive_dir.mkdir(parents=True, exist_ok=True)
        tar_path = archive_dir / f"{workspace.name}.tar.gz"
        with tarfile.open(tar_path, mode="w:gz") as tar:
            if workspace.exists():
                tar.add(workspace, arcname=workspace.name)
        shutil.rmtree(workspace, ignore_errors=True)
        return tar_path
