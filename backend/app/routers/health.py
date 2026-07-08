import requests
from fastapi import APIRouter

from app.clients.trino_client import trino_client
from app.config import settings

router = APIRouter()


@router.get("/health")
def health():
    checks = {}

    try:
        trino_client.execute("SELECT 1")
        checks["trino"] = "ok"
    except Exception as e:
        checks["trino"] = f"error: {e}"

    try:
        requests.post(settings.dagster_graphql_url, json={"query": "{ __typename }"}, timeout=5).raise_for_status()
        checks["dagster"] = "ok"
    except Exception as e:
        checks["dagster"] = f"error: {e}"

    try:
        requests.get(f"{settings.qdrant_url}/collections/{settings.qdrant_collection}", timeout=5).raise_for_status()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"error: {e}"

    try:
        requests.get(f"{settings.pipelines_url}/", timeout=5).raise_for_status()
        checks["pipelines"] = "ok"
    except Exception as e:
        checks["pipelines"] = f"error: {e}"

    return checks
