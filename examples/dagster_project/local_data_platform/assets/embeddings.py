import uuid

from dagster import AssetExecutionContext, AssetKey, asset
from qdrant_client.models import PointStruct

from local_data_platform.resources import OllamaResource, QdrantResource, TrinoResource

# Fixed namespace so uuid5(NAMESPACE, natural_key) is stable across runs,
# giving deterministic point IDs that upsert instead of duplicating.
NAMESPACE = uuid.UUID("6f6a6f0e-6e61-4b0f-9c9a-9f6b3a9d6a10")


@asset(group_name="ai", compute_kind="python", deps=[AssetKey(["marts", "curated_events"])])
def curated_events_embeddings(
    context: AssetExecutionContext,
    trino: TrinoResource,
    ollama: OllamaResource,
    qdrant: QdrantResource,
) -> None:
    """Embeds iceberg.marts.curated_events rows into Qdrant for RAG.

    v1 simplification: embeds rows one at a time via HTTP calls to Ollama —
    fine at this data volume, batching is the natural follow-up once row
    counts grow. Only the hourly curated grain is embedded, not raw events.
    """
    qdrant.ensure_collection()

    rows = trino.execute(
        "SELECT user_id, event_type, event_hour, event_count FROM iceberg.marts.curated_events"
    )

    points = []
    for user_id, event_type, event_hour, event_count in rows:
        text = f"On {event_hour}, user {user_id} generated {event_count} '{event_type}' events."
        vector = ollama.embed(text)
        point_id = str(uuid.uuid5(NAMESPACE, f"{user_id}|{event_type}|{event_hour}"))
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "user_id": user_id,
                    "event_type": event_type,
                    "event_hour": str(event_hour),
                    "event_count": event_count,
                    "source_table": "iceberg.marts.curated_events",
                    "text": text,
                },
            )
        )

    if points:
        qdrant.upsert(points)

    context.log.info(f"Upserted {len(points)} vectors into Qdrant collection '{qdrant.collection}'")
