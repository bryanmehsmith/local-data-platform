import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str = os.environ.get("BACKEND_API_KEY", "")

    trino_host: str = os.environ.get("TRINO_HOST", "trino")
    trino_port: int = int(os.environ.get("TRINO_PORT", "8080"))
    trino_user: str = "backend"
    trino_catalog: str = os.environ.get("TRINO_CATALOG", "iceberg")

    dagster_graphql_url: str = os.environ.get(
        "DAGSTER_GRAPHQL_URL", "http://dagster-webserver:3000/graphql"
    )

    qdrant_url: str = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    qdrant_collection: str = os.environ.get("QDRANT_COLLECTION", "curated_events")

    ollama_base_url: str = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
    ollama_embed_model: str = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    pipelines_url: str = os.environ.get("PIPELINES_URL", "http://pipelines:9099")
    pipelines_api_key: str = os.environ.get("OPENWEBUI_PIPELINES_API_KEY", "0p3n-w3bu!")

    cors_origins: list[str] = ["http://localhost:3200"]

    # Kept as a raw string (not list[str]) because pydantic-settings tries to
    # JSON-decode env values for list-typed fields — split at the call site.
    backend_plugin_dirs_raw: str = os.environ.get("BACKEND_PLUGIN_DIRS", "")

    @property
    def backend_plugin_dirs(self) -> list[str]:
        return [p.strip() for p in self.backend_plugin_dirs_raw.split(",") if p.strip()]


settings = Settings()
