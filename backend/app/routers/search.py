from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.clients.search_client import search_client

router = APIRouter()


class SearchRequest(BaseModel):
    text: str
    top_k: int = 5
    collection: str | None = None


@router.post("/query")
def search_query(req: SearchRequest):
    try:
        results = search_client.search(req.text, req.top_k, req.collection)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search failed: {e}")
    return {"results": results}
