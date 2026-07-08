import json
import uuid

from dagster import AssetExecutionContext, asset

from local_data_platform.assets.dbt_assets import DBT_PROJECT_DIR, dbt_project_assets
from local_data_platform.resources import OllamaResource, QdrantResource

NAMESPACE = uuid.UUID("6f6a6f0e-6e61-4b0f-9c9a-9f6b3a9d6a10")


@asset(group_name="ai", compute_kind="python", deps=[dbt_project_assets])
def dbt_docs_embeddings(
    context: AssetExecutionContext,
    ollama: OllamaResource,
    qdrant_docs: QdrantResource,
) -> None:
    """Embeds dbt model/column descriptions from manifest.json into a
    separate Qdrant collection so RAG can answer "what does this table
    mean" questions, additive to the row-fact embeddings in
    curated_events_embeddings (which uses a different QdrantResource
    instance pointed at the "curated_events" collection).
    """
    from qdrant_client.models import PointStruct

    qdrant_docs.ensure_collection()

    with open(f"{DBT_PROJECT_DIR}/target/manifest.json") as f:
        manifest = json.load(f)

    points = []
    for node_id, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") != "model":
            continue
        name = node["name"]
        description = node.get("description") or "(no description)"
        columns = node.get("columns", {})
        col_text = "; ".join(
            f"{c}: {v.get('description') or 'no description'}" for c, v in columns.items()
        )
        text = f"dbt model '{name}': {description}. Columns: {col_text}"
        vector = ollama.embed(text)
        point_id = str(uuid.uuid5(NAMESPACE, f"dbt_doc|{name}"))
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={"model_name": name, "source_table": "dbt_docs", "text": text},
            )
        )

    if points:
        qdrant_docs.upsert(points)

    context.log.info(f"Upserted {len(points)} dbt doc vectors into '{qdrant_docs.collection}'")
