from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer

from .orchestrator import Orchestrator
from .tracker.linear_client import LinearClient
from .workflow_loader import load_workflow

app = typer.Typer(add_completion=False)


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")


@app.command()
def validate(workflow: Path = typer.Option(..., exists=True, dir_okay=False)) -> None:
    bundle = load_workflow(workflow)
    typer.echo(f"OK: {bundle.source_path}")
    typer.echo(f"project_slug = {bundle.config.tracker.project_slug}")
    typer.echo(f"workspace_root = {bundle.config.workspace.root}")
    typer.echo(f"max_concurrent_agents = {bundle.config.agent.max_concurrent_agents}")


@app.command()
def run(workflow: Path = typer.Option(..., exists=True, dir_okay=False), verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    configure_logging(verbose=verbose)
    bundle = load_workflow(workflow)

    async def _main() -> None:
        linear = LinearClient(api_key=bundle.config.tracker.api_key)
        try:
            orchestrator = Orchestrator(workflow=bundle, linear=linear)
            await orchestrator.run_forever()
        finally:
            await linear.aclose()

    asyncio.run(_main())


@app.command("serve-ops")
def serve_ops(workflow: Path = typer.Option(..., exists=True, dir_okay=False), host: str = typer.Option("127.0.0.1"), port: int = typer.Option(8080)) -> None:
    import uvicorn
    from .api.app import build_api

    bundle = load_workflow(workflow)
    linear = LinearClient(api_key=bundle.config.tracker.api_key)
    orchestrator = Orchestrator(workflow=bundle, linear=linear)
    app_obj = build_api(
        orchestrator=orchestrator,
        workspace_root=bundle.config.workspace.root,
        thread_index_file=(bundle.config.thread_catalog.index_file or str(Path(bundle.config.workspace.root) / "_thread_index.json")),
        codex_config=bundle.config.codex,
        admin_token=bundle.config.admin_api.token,
    )
    uvicorn.run(app_obj, host=host, port=port)
