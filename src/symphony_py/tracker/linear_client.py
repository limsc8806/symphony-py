from __future__ import annotations

from typing import Any

import httpx

from ..models import Issue


class LinearAPIError(RuntimeError):
    pass


class LinearClient:
    def __init__(self, api_key: str, timeout: float = 20.0) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://api.linear.app/graphql",
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post("", json={"query": query, "variables": variables})
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise LinearAPIError(str(payload["errors"]))
        return payload.get("data", {})

    async def list_active_issues(self, project_slug: str, active_states: list[str], limit: int = 50) -> list[Issue]:
        query = """
        query IssuesForProject($projectSlug: String!, $activeStates: [String!], $limit: Int!) {
          issues(first: $limit, filter: { project: { slug: { eq: $projectSlug } }, state: { name: { in: $activeStates } } }, orderBy: priority) {
            nodes {
              id identifier title description priority url
              labels { nodes { name } }
              state { name type }
            }
          }
        }
        """
        data = await self._graphql(query, {"projectSlug": project_slug, "activeStates": active_states, "limit": limit})
        rows = []
        for node in data.get("issues", {}).get("nodes", []):
            rows.append(Issue(
                id=node["id"], identifier=node["identifier"], title=node.get("title", ""),
                description=node.get("description", ""), priority=int(node.get("priority") or 0),
                state_name=node["state"]["name"], state_type=node["state"].get("type"),
                labels=[x["name"] for x in node.get("labels", {}).get("nodes", [])], url=node.get("url")
            ))
        return rows

    async def get_workflow_state_id(self, project_slug: str, state_name: str) -> str:
        query = """
        query ProjectStates($projectSlug: String!) {
          projects(filter: { slug: { eq: $projectSlug } }, first: 1) {
            nodes { states { nodes { id name } } }
          }
        }
        """
        data = await self._graphql(query, {"projectSlug": project_slug})
        projects = data.get("projects", {}).get("nodes", [])
        if not projects:
            raise LinearAPIError("Project not found")
        for state in projects[0]["states"]["nodes"]:
            if state["name"] == state_name:
                return state["id"]
        raise LinearAPIError("State not found")

    async def transition_issue_state(self, issue_id: str, state_id: str) -> None:
        mutation = """
        mutation MoveIssue($issueId: String!, $stateId: String!) {
          issueUpdate(id: $issueId, input: { stateId: $stateId }) { success }
        }
        """
        data = await self._graphql(mutation, {"issueId": issue_id, "stateId": state_id})
        if not data.get("issueUpdate", {}).get("success"):
            raise LinearAPIError("Failed to move issue")

    async def comment_on_issue(self, issue_id: str, body: str) -> None:
        mutation = """
        mutation CommentIssue($issueId: String!, $body: String!) {
          commentCreate(input: { issueId: $issueId, body: $body }) { success }
        }
        """
        data = await self._graphql(mutation, {"issueId": issue_id, "body": body})
        if not data.get("commentCreate", {}).get("success"):
            raise LinearAPIError("Failed to comment")
