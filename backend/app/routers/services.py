import asyncio

import httpx
from fastapi import APIRouter

from app.services_registry import SERVICES

router = APIRouter()


async def _check_service(client: httpx.AsyncClient, svc: dict) -> dict:
    try:
        resp = await client.get(svc["check_url"], timeout=2)
        status = "ok" if resp.status_code < 500 else "error"
    except Exception:
        status = "error"
    return {
        "key": svc["key"],
        "name": svc["name"],
        "category": svc["category"],
        "external_url": svc["external_url"],
        "status": status,
    }


@router.get("")
async def list_services():
    async with httpx.AsyncClient() as client:
        return await asyncio.gather(*(_check_service(client, svc) for svc in SERVICES))
