import requests
from qdrant_client import QdrantClient

from app.config import settings


class SearchClient:
    def __init__(self):
        self._qdrant: QdrantClient | None = None

    def _client(self) -> QdrantClient:
        if self._qdrant is None:
            self._qdrant = QdrantClient(url=settings.qdrant_url)
        return self._qdrant

    def embed(self, text: str) -> list[float]:
        resp = requests.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

    def search(self, text: str, top_k: int = 5, collection: str | None = None) -> list[dict]:
        vector = self.embed(text)
        hits = (
            self._client()
            .query_points(
                collection_name=collection or settings.qdrant_collection,
                query=vector,
                limit=top_k,
            )
            .points
        )
        return [{"score": h.score, "payload": h.payload} for h in hits]


search_client = SearchClient()
