import requests

from app.config import settings

# Verified live against this repo's running Dagster instance (see
# docs/runbooks/phase9-app-layer.md) before writing this client — Dagster's
# GraphQL schema shifts across releases, so don't trust these field names
# without re-checking if the Dagster version ever changes.
REPOSITORY_NAME = "__repository__"
REPOSITORY_LOCATION_NAME = "local_data_platform"
ASSET_JOB_NAME = "__ASSET_JOB"


class DagsterClient:
    def _query(self, query: str, variables: dict | None = None) -> dict:
        resp = requests.post(
            settings.dagster_graphql_url,
            json={"query": query, "variables": variables or {}},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        if "errors" in body:
            raise RuntimeError(body["errors"])
        return body["data"]

    def list_assets(self) -> list[dict]:
        data = self._query("query { assetNodes { assetKey { path } description jobNames } }")
        return [
            {
                "key": "/".join(node["assetKey"]["path"]),
                "description": node.get("description"),
                "jobs": node["jobNames"],
            }
            for node in data["assetNodes"]
        ]

    def materialize(self, asset_key: str) -> dict:
        path = asset_key.split("/")
        data = self._query(
            """
            mutation($executionParams: ExecutionParams!) {
              launchPipelineExecution(executionParams: $executionParams) {
                __typename
                ... on LaunchRunSuccess { run { id status } }
                ... on PythonError { message }
                ... on InvalidSubsetError { message }
                ... on RunConfigValidationInvalid { errors { message } }
                ... on PipelineNotFoundError { message }
              }
            }
            """,
            {
                "executionParams": {
                    "selector": {
                        "repositoryName": REPOSITORY_NAME,
                        "repositoryLocationName": REPOSITORY_LOCATION_NAME,
                        "jobName": ASSET_JOB_NAME,
                        "assetSelection": [{"path": path}],
                    }
                }
            },
        )
        result = data["launchPipelineExecution"]
        if result["__typename"] != "LaunchRunSuccess":
            raise RuntimeError(f"{result['__typename']}: {result.get('message', result)}")
        return {"run_id": result["run"]["id"], "status": result["run"]["status"]}

    def get_run(self, run_id: str) -> dict:
        data = self._query(
            """
            query($runId: ID!) {
              runOrError(runId: $runId) {
                __typename
                ... on Run { id status startTime endTime }
                ... on RunNotFoundError { message }
              }
            }
            """,
            {"runId": run_id},
        )
        result = data["runOrError"]
        if result["__typename"] != "Run":
            raise RuntimeError(result.get("message", result))
        return {
            "run_id": result["id"],
            "status": result["status"],
            "started_at": result.get("startTime"),
            "ended_at": result.get("endTime"),
        }


dagster_client = DagsterClient()
