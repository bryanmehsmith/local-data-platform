# Local Data Platform

A modern, on-prem/local data platform for batch and streaming ETL, built on
an open object-storage lakehouse — plus a local, on-prem AI chat layer with
retrieval-augmented generation (RAG) over the lakehouse data. Runs on a
single machine today and scales to a small cluster later without changing
tools.

| Layer | Tool |
|---|---|
| Batch orchestration | [Dagster](https://dagster.io) |
| Streaming | [Redpanda](https://redpanda.com) |
| Object storage | [MinIO](https://min.io) |
| Table catalog | [Nessie](https://projectnessie.org) (Iceberg REST catalog) |
| Query engine | [Trino](https://trino.io) + [DuckDB](https://duckdb.org) |
| Table format / transforms | [Apache Iceberg](https://iceberg.apache.org), [dbt](https://www.getdbt.com) |
| Local LLM | [Ollama](https://ollama.com) |
| Chat UI | [Open WebUI](https://openwebui.com) |
| RAG | [open-webui/pipelines](https://github.com/open-webui/pipelines), [Qdrant](https://qdrant.tech) |
| BI / dashboards | [Metabase](https://www.metabase.com) |
| Observability | [Prometheus](https://prometheus.io), [Grafana](https://grafana.com), [Loki](https://grafana.com/oss/loki/), [cAdvisor](https://github.com/google/cadvisor) |
| Application layer | [FastAPI](https://fastapi.tiangolo.com) backend, [React](https://react.dev) + [Vite](https://vite.dev) frontend |

See `docs/architecture.md` for the full design and `docs/runbooks/` for
step-by-step phase instructions.

## Quickstart (Phase 1 — storage, catalog, query engine)

```bash
cp .env.example .env        # then edit secrets as needed
docker compose --env-file .env -f docker/docker-compose.yml up -d minio minio-init nessie trino
```

(`--env-file .env` is required because Compose otherwise looks for `.env`
next to the compose file in `docker/`, not the repo root — or just use
`make phase1`.)

Then follow `docs/runbooks/phase1-storage-catalog-query.md` to create and
query your first Iceberg table.

## Bring up everything

```bash
make up          # brings up every phase (1-8), with GPU-accelerated Ollama
make up-nogpu    # same, but with CPU-only Ollama (no NVIDIA GPU required)
```

(First run seeds `workload/` from the bundled `examples/` scenario
automatically — see "Repo layout" below. No manual setup needed.)

Both targets chain every phase in order — storage/catalog/query,
orchestration, streaming, local AI chat/RAG (Ollama, Qdrant, Open WebUI,
pipelines), BI dashboards (Metabase, with its admin account and starter
dashboard bootstrapped automatically), dbt tests + dbt-docs, text-to-SQL +
eval harness, and observability (Prometheus, Grafana, Loki, Promtail,
cAdvisor) — but not the application layer, which is a separate opt-in step:

```bash
make phase9  # + application layer (FastAPI backend, React/Vite frontend)
```

Individual phases can also be run standalone (each will bring up its own
prerequisites first):

```bash
make phase1  # storage, catalog, query engine
make phase2  # + batch orchestration (Dagster)
make phase3  # + streaming (Redpanda)
make phase4  # + local AI chat/RAG layer (CPU)
make phase4-gpu  # + local AI chat/RAG layer (GPU-accelerated, requires nvidia-container-toolkit)
make phase5  # + BI dashboards (Metabase)
make phase6  # + dbt tests (as Dagster asset checks) + dbt-docs static site
make phase7  # + text-to-SQL pipeline, richer RAG (dbt docs), eval harness — assumes Phase 4 (either variant) is already up
make phase8  # + observability (Prometheus, Grafana, Loki, Promtail, cAdvisor)
```

Equivalent raw commands are in the `Makefile`. `make down`/`make logs`/`make ps`
act on the full set of services across every phase. See
`docs/runbooks/phase4-local-ai.md` for GPU setup details.

- MinIO console: http://localhost:9001
- Nessie API: http://localhost:19120
- Trino UI: http://localhost:8080
- Redpanda Console: http://localhost:8090
- Dagster UI: http://localhost:3000
- Open WebUI (chat): http://localhost:3100
- Ollama API: http://localhost:11434
- Qdrant: http://localhost:6333
- Pipelines (RAG sidecar): http://localhost:9099
- Metabase (dashboards): http://localhost:3400
- dbt docs (catalog/lineage): http://localhost:8070
- Grafana (dashboards): http://localhost:3300
- Prometheus: http://localhost:9090
- cAdvisor: http://localhost:8081
- Loki (via Grafana Explore only, no standalone UI): http://localhost:3500
- App frontend: http://localhost:3200
- App backend API: http://localhost:8000/api

Open WebUI's model dropdown offers two chat models: **Lakehouse RAG**
(answers from pre-embedded facts + dbt docs) and **Lakehouse Text-to-SQL**
(generates and runs live, read-only Trino SQL for open-ended questions).
`workload/evals/run_rag_eval.py` is a lightweight, manual regression check for both —
see `docs/runbooks/phase7-ai-expansion.md`.

## Repo layout

This repo is the **infrastructure repo** — Docker Compose files, service
config, the backend/frontend app layer, docs, and a bundled reference
example in `examples/` (Dagster assets, dbt models, RAG pipelines, sample
producer, eval harness). It's meant to be reusable across projects.

Docker Compose, the backend plugin loader, and the frontend route
auto-discovery all actually read from `workload/` — a folder gitignored
here, meant to hold your own independently-versioned private repo for
scenario-specific work. `make init-workload` (run automatically by
`make phase2`/`phase3`/`phase9`) copies `examples/` into `workload/`
whenever `workload/dagster_project` doesn't exist yet (no-clobber, so any
files you already have there are untouched), so `make up` works out of the
box on a fresh clone with no setup — clone your own repo into `workload/`
instead whenever you're ready to replace the bundled example. See
`examples/README.md` and
`workload/README.md` for details.
