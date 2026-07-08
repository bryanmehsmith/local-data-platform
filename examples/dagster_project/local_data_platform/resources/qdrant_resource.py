import os

from dagster import ConfigurableResource
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class QdrantResource(ConfigurableResource):
    url: str = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    collection: str = os.environ.get("QDRANT_COLLECTION", "curated_events")
    vector_size: int = 768  # nomic-embed-text output dim

    def get_client(self) -> QdrantClient:
        return QdrantClient(url=self.url)

    def ensure_collection(self) -> None:
        client = self.get_client()
        if not client.collection_exists(self.collection):
            client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

    def upsert(self, points: list[PointStruct]) -> None:
        self.get_client().upsert(collection_name=self.collection, points=points)
