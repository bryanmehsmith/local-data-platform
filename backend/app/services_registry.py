SERVICES = [
    # --- Storage / catalog ---
    {
        "key": "minio_console",
        "name": "MinIO Console",
        "category": "storage",
        "check_url": "http://minio:9000/minio/health/live",
        "external_url": "http://localhost:9001",
    },
    {
        "key": "nessie",
        "name": "Nessie",
        "category": "catalog",
        "check_url": "http://nessie:19120/api/v2/config",
        "external_url": "http://localhost:19120",
    },
    # --- Compute ---
    {
        "key": "trino",
        "name": "Trino UI",
        "category": "compute",
        "check_url": "http://trino:8080/v1/info",
        "external_url": "http://localhost:8080",
    },
    {
        "key": "dagster",
        "name": "Dagster UI",
        "category": "compute",
        "check_url": "http://dagster-webserver:3000/server_info",
        "external_url": "http://localhost:3000",
    },
    # --- Streaming ---
    {
        "key": "redpanda_console",
        "name": "Redpanda Console",
        "category": "streaming",
        "check_url": "http://redpanda-console:8080/",
        "external_url": "http://localhost:8090",
    },
    # --- AI ---
    {
        "key": "open_webui",
        "name": "Open WebUI",
        "category": "ai",
        "check_url": "http://open-webui:8080/",
        "external_url": "http://localhost:3100",
    },
    {
        "key": "ollama",
        "name": "Ollama API",
        "category": "ai",
        "check_url": "http://ollama:11434/api/tags",
        "external_url": "http://localhost:11434",
    },
    {
        "key": "qdrant",
        "name": "Qdrant",
        "category": "ai",
        "check_url": "http://qdrant:6333/collections",
        "external_url": "http://localhost:6333/dashboard",
    },
    {
        "key": "pipelines",
        "name": "Pipelines (RAG sidecar)",
        "category": "ai",
        "check_url": "http://pipelines:9099/",
        "external_url": "http://localhost:9099",
    },
    # --- BI / catalog docs ---
    {
        "key": "metabase",
        "name": "Metabase",
        "category": "bi",
        "check_url": "http://metabase:3000/api/health",
        "external_url": "http://localhost:3400",
    },
    {
        "key": "dbt_docs",
        "name": "dbt Docs",
        "category": "bi",
        "check_url": "http://dbt-docs:80/index.html",
        "external_url": "http://localhost:8070",
    },
    # --- Observability ---
    {
        "key": "grafana",
        "name": "Grafana",
        "category": "observability",
        "check_url": "http://grafana:3000/api/health",
        "external_url": "http://localhost:3300",
    },
    {
        "key": "prometheus",
        "name": "Prometheus",
        "category": "observability",
        "check_url": "http://prometheus:9090/-/healthy",
        "external_url": "http://localhost:9090",
    },
    {
        "key": "cadvisor",
        "name": "cAdvisor",
        "category": "observability",
        "check_url": "http://cadvisor:8080/healthz",
        "external_url": "http://localhost:8081",
    },
]
