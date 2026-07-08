from dagster import Definitions
from dagster_dbt import DbtCliResource

from local_data_platform.assets import (
    raw_events_seed,
    landed_events,
    dbt_project_assets,
    curated_events_embeddings,
    dbt_docs_embeddings,
)
from local_data_platform.assets.dbt_assets import DBT_PROJECT_DIR
from local_data_platform.jobs import land_raw_events_job
from local_data_platform.resources import TrinoResource, MinioResource, OllamaResource, QdrantResource
from local_data_platform.sensors import redpanda_landing_sensor

defs = Definitions(
    assets=[
        raw_events_seed,
        landed_events,
        dbt_project_assets,
        curated_events_embeddings,
        dbt_docs_embeddings,
    ],
    jobs=[land_raw_events_job],
    sensors=[redpanda_landing_sensor],
    resources={
        "trino": TrinoResource(),
        "minio": MinioResource(),
        "ollama": OllamaResource(),
        "qdrant": QdrantResource(),
        "qdrant_docs": QdrantResource(collection="dbt_docs"),
        "dbt": DbtCliResource(project_dir=DBT_PROJECT_DIR, profiles_dir=DBT_PROJECT_DIR),
    },
)
