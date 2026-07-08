from fastapi import APIRouter, HTTPException

from app.clients.dagster_client import dagster_client

router = APIRouter()


@router.get("/assets")
def list_assets():
    return dagster_client.list_assets()


@router.post("/assets/{asset_key:path}/materialize")
def materialize_asset(asset_key: str):
    try:
        return dagster_client.materialize(asset_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    try:
        return dagster_client.get_run(run_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
