import requests
from fastapi import APIRouter

from app.services_registry import SERVICES

router = APIRouter()


@router.get("")
def list_services():
    result = []
    for svc in SERVICES:
        try:
            resp = requests.get(svc["check_url"], timeout=2)
            status = "ok" if resp.status_code < 500 else "error"
        except Exception:
            status = "error"
        result.append(
            {
                "key": svc["key"],
                "name": svc["name"],
                "category": svc["category"],
                "external_url": svc["external_url"],
                "status": status,
            }
        )
    return result
