"""Template: drop scenario-specific FastAPI routers here.

Every *.py file in this directory (except ones starting with `_`) is loaded
by the infra repo's `backend/app/plugin_loader.py` at startup and mounted
onto the running backend — no changes to core `backend/` code required.

Convention (all module-level, all optional except `router`):
  router: APIRouter        -- required; the router to mount
  prefix: str               -- default "/api/workload/<this file's stem>"
  tags: list[str]           -- default ["workload"]
  require_auth: bool        -- default True (same shared X-API-Key as core routers)

Copy this file, rename it, and replace the example route with your own.
Delete it once you no longer need the example.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/example")
def example():
    return {"message": "Hello from the workload backend plugin."}
