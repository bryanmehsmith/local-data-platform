# Architecture

## Goal

A modern, on-prem/local data platform for batch and streaming ETL that runs
comfortably on a single machine today and scales to a small cluster later
without swapping tools — plus a local, on-prem AI chat layer with
retrieval-augmented generation (RAG) grounded in the lakehouse data.

## Component map

| Layer | Tool | Notes |
|---|---|---|
| Batch orchestration | **Dagster** | Asset-based lineage; `dagster-dbt` turns dbt models into Dagster assets automatically |
| Streaming | **Redpanda** | Kafka-API compatible — any Kafka client/library works unmodified |
| Object storage (datalake) | **MinIO** | S3 API; single-node today, distributed erasure-coded mode later |
| Table format + catalog | **Apache Iceberg + Nessie** | Nessie is a REST catalog with git-like versioned metadata |
| Query engine | **Trino** (+ DuckDB for local/dev) | Distributed SQL over Iceberg tables in MinIO |
| Stream landing | **Redpanda Connect** (Benthos) | Config-driven, lands events as gzipped NDJSON in MinIO |
| Transformation | **dbt** (dbt-trino) | SQL-as-code, materializes Iceberg tables via Trino |
| Local LLM runtime | **Ollama** | OpenAI-compatible API, CPU by default, GPU via a Compose override, no rewrite |
| Chat UI | **Open WebUI** | Talks to Ollama directly for plain chat, and to the `pipelines` sidecar for RAG |
| RAG orchestration | **open-webui/pipelines** | Custom FastAPI sidecar implementing the retrieval step (`workload/pipelines/rag_lakehouse_pipeline.py`) and text-to-SQL (`text_to_sql_pipeline.py`) |
| Vector store | **Qdrant** | Two collections: `curated_events` (data facts) and `dbt_docs` (table documentation) |
| BI / dashboards | **Metabase** | Native Trino driver; connects to catalog `iceberg`, schema `marts` |
| Data quality | **dbt tests** | `not_null`/`unique`/`relationships` tests, surfaced as Dagster asset checks |
| Catalog / lineage | **dbt docs** (static site) | Served via nginx; searchable docs + lineage DAG, no dedicated catalog tool |
| Metrics | **Prometheus** | Scrapes native endpoints (Redpanda, Qdrant, MinIO) + cAdvisor |
| Container resource metrics | **cAdvisor** | CPU/mem/network per container (see known limitation below) |
| Centralized logs | **Loki + Promtail** | Promtail ships every container's logs via Docker service discovery — zero config on the other services |
| Dashboards / alerting UI | **Grafana** | Pre-provisioned Prometheus + Loki datasources and 3 starter dashboards |
| Application backend | **FastAPI** | Exposes Trino (incl. schema/table/column browsing)/Dagster/chat/search/services-health as a REST API; single shared API key auth |
| Application frontend | **React + Vite + Tailwind** | SPA with one page per backend router, a schema/table browser, and a services hub linking to every other UI in the platform |

## Data flow

```
workload/sample_producer/produce_events.py
        │  (JSON events)
        ▼
   Redpanda topic "raw.events"  ◄── inspectable via Redpanda Console
        │
        ▼
  Redpanda Connect (events-to-minio.yaml)
        │  batches + gzips NDJSON
        ▼
  MinIO bucket "raw" (s3://raw/events/dt=.../hour=.../*.json.gz)
        │
        ▼
  Dagster asset `landed_events`  (reads gzip files via boto3, INSERTs via Trino)
        │
        ▼
  Iceberg table iceberg.raw.events  (managed by Nessie catalog, stored in s3://warehouse/)
        │
        ▼
  dbt model stg_events   (dedupe by event_id, via Trino)
        │
        ▼
  dbt model curated_events  (hourly aggregates, via Trino)
        │
        ▼
  Queried via Trino (BI/JDBC) or DuckDB (ad hoc/local)
```

The whole chain from `landed_events` through `curated_events` is one asset
graph in the Dagster UI, materializable on a schedule or via the
`redpanda_landing_sensor` sensor (polls MinIO for new landed files every 30s).

A second branch continues from the curated mart into the AI layer:

```
  iceberg.marts.curated_events
        │
        ▼
  Dagster asset `curated_events_embeddings`
        │  renders each row as text, embeds via Ollama (nomic-embed-text)
        ▼
  Qdrant collection "curated_events"  (one point per user/event_type/hour, upserted)
        │
        ▼
  pipelines sidecar (rag_lakehouse_pipeline.py)
        │  embeds the user's question, searches Qdrant top-K, builds an augmented prompt
        ▼
  Ollama chat completion (llama3.2:3b)
        │
        ▼
  Open WebUI  (http://localhost:3100)
```

A parallel branch embeds dbt's own model documentation into a second
collection, so RAG can answer "what does this table mean" questions too:

```
  workload/dbt_project/target/manifest.json  (model/column descriptions from Phase 6a)
        │
        ▼
  Dagster asset `dbt_docs_embeddings`
        │
        ▼
  Qdrant collection "dbt_docs"
        │
        ▼
  pipelines sidecar (rag_lakehouse_pipeline.py searches BOTH collections)
```

A separate pipeline answers open-ended questions by generating and running
live SQL instead of relying on pre-embedded facts:

```
  User question
        │
        ▼
  pipelines sidecar (text_to_sql_pipeline.py)
        │  Ollama generates SQL → app-level regex guard → Trino (read-only user)
        ▼
  Ollama turns the query result into a plain-language answer
```

A third branch continues from the same curated mart into BI:

```
  iceberg.marts.curated_events
        │
        ▼
  Metabase (native Trino driver)  →  "Curated Events Overview" dashboard  (http://localhost:3400)
```

A fourth branch turns the platform's primitives into a browsable app:

```
  Browser (http://localhost:3200)
        │
        ▼
  React/Vite frontend  (QueryPage, AssetsPage, ChatPage, SearchPage, ServicesPage)
        │  fetch() with X-API-Key header
        ▼
  FastAPI backend  (http://localhost:8000/api)
        │
        ├──▶ Trino (read-only guarded SQL, schema/table/column browsing)
        ├──▶ Dagster GraphQL (list/materialize/poll assets)
        ├──▶ pipelines sidecar (chat, either model)
        ├──▶ Ollama + Qdrant (vector search)
        └──▶ every other service's health-check endpoint (services hub)
```

## Why a custom app layer instead of just the existing UIs

Dagster's UI, Open WebUI, and Metabase are each excellent at their one job,
but none of them let you compose a workflow across the platform (e.g. "run
this query, then trigger this asset, then ask a question about the
result") without switching tools. The FastAPI backend gives a single,
scriptable API surface over Trino/Dagster/chat/search, and the React
frontend is a starting scaffold — one page per backend router, plus a
services hub linking out to every other UI in the platform — meant to be
extended with whatever cross-cutting views the platform's actual usage calls
for, rather than a fixed-purpose dashboard.

**Scenario-specific extensions live in `workload/`, not core
`backend`/`frontend`.** `workload/` is gitignored by this repo — it's meant
to hold your own independently-versioned private repo. `examples/` (tracked
here, the bundled reference scenario) has the same internal layout;
`make init-workload` copies it into `workload/` (no-clobber) whenever
`workload/dagster_project` doesn't exist yet, so the whole platform runs
out of the box on a fresh clone with no setup. Clone your own repo into
`workload/` whenever you're ready to replace the bundled example —
nothing else in this repo needs to change.

`workload/backend/*.py` files are loaded at startup by
`backend/app/plugin_loader.py` (bind-mounted read-only, scanned via
`importlib`, one `APIRouter` per file) and mounted under
`/api/workload/<name>` — a broken plugin logs a warning and is skipped
rather than crashing core startup. `workload/frontend/src/routes/*.tsx`
files are discovered at *build time* by `frontend/src/routes-manifest.ts`
via Vite's `import.meta.glob` (the frontend has no runtime plugin loading —
it's a static build served by nginx) and merged into the router and sidebar
nav alongside the core pages. Both are documented, working templates (see
`examples/backend/example_plugin.py`, `examples/frontend/src/routes/ExamplePage.tsx`)
meant to be copied and replaced, not core files a real adopter needs to
fork. **Known v1 simplification**: there's no dependency isolation between
workload plugins and the core app (same Python process, same JS bundle) —
fine for a single trusted workload repo, not a substitute for a real
multi-tenant plugin sandbox.

## Why Ollama + Open WebUI + Pipelines + Qdrant

Ollama gives an OpenAI-compatible local API that runs CPU-only today and
picks up an NVIDIA GPU transparently if one is passed through later (a
Compose override, not a rewrite). Open WebUI is the most widely used
open-source ChatGPT-like frontend and speaks Ollama's API natively. Its
"Pipelines" plugin framework is the supported way to inject custom retrieval
logic in front of a chat completion, which is what lets the platform answer
questions from `iceberg.marts.curated_events` instead of only the model's
training data. Qdrant was chosen over adding another Postgres/pgvector
dependency because it's a single lightweight container with no schema setup
required for vector storage.

## Why Metabase over Superset

Superset realistically needs its own Postgres (metadata DB), Redis
(caching/Celery broker), a Celery worker, and a beat scheduler alongside the
app container itself — 4-5 containers for one dashboard, and its official
image doesn't bundle a Trino driver (one would need to be pip-installed into
a custom image layer). Metabase ships as a single container with an
embedded H2 app database and a native, first-party Trino-compatible driver
built in. For two marts, one container is the right amount of infrastructure.

## Data quality

`dagster-dbt`'s `@dbt_assets` decorator already runs `dbt build`, which runs
dbt tests as part of the same invocation — adding tests is purely a YAML
change (`workload/dbt_project/models/{staging,marts}/schema.yml`), no code change.
Each test becomes a Dagster **asset check** shown on the corresponding
model's "Checks" tab, red on failure. Coverage: `not_null`/`unique` on
`stg_events.event_id`, `not_null` across both models' columns, and a
`relationships` test asserting every `curated_events.user_id` exists in
`stg_events` — the one meaningful FK-like relationship in this two-model
project.

## Catalog / lineage — why not a dedicated tool

OpenMetadata, DataHub, and Amundsen all realistically need 4-6 containers
(a metadata database, a search index like Elasticsearch/OpenSearch, an
ingestion scheduler, the app itself) — disproportionate for cataloging two
dbt models. Instead, `dbt docs generate` produces a searchable static site
(column descriptions, a lineage DAG, source freshness) from artifacts the
pipeline already creates, served by a single nginx container. Nessie's own
commit-log UI (`:19120`) covers table-level version history. Revisit a
dedicated catalog tool once there are many more models, multiple non-Trino
sources, or a second engineer who needs search/ownership/tagging — at that
scale the footprint becomes justified.

## Observability

Two independent data paths, both feeding Grafana:

- **Metrics**: Redpanda, Qdrant, and MinIO each expose a native Prometheus
  endpoint, scraped directly. Trino, Dagster, and Ollama don't have
  reliable native Prometheus integrations at the versions pinned here — for
  those, cAdvisor's container-level CPU/mem/network stands in as a coarse
  health signal.
- **Logs**: Promtail discovers every container via the Docker socket
  (`docker_sd_configs`) and ships stdout/stderr to Loki — zero
  configuration required on the other 20 services.

**Known limitation, found during verification, not assumed:** cAdvisor
cannot correlate individual application containers under this Docker
Desktop for Windows setup — its container-identification code expects the
classic dockerd + overlay2 `layerdb` layout, which doesn't match Docker
Desktop's containerd-backed image store. Only coarse root-cgroup metrics
(`id="/"`, `id="/docker"`) are available; the per-container panels in the
"Container Resources" Grafana dashboard will show no data for the platform's
own containers on this host. This is a host/Docker-Desktop configuration
issue, not a bug in this repo's Compose config — revisit on a native Linux
Docker host. The Trino JMX Prometheus exporter (would need a custom image
bundling the JMX agent jar) is a documented stretch goal, not built in v1
to avoid a fragile half-implementation.

## Why Nessie over Lakekeeper

Nessie has the longest track record integrating with Trino, Spark, and
dbt-trino, ships an official Docker image, and gives git-like branching
semantics on the catalog (useful for safe blue-green table swaps later).
Lakekeeper is newer and less battle-tested with Trino as of writing. Because
both speak the Iceberg REST catalog API, switching later is a Trino/dbt/Dagster
config change, not a rewrite.

## Known v1 simplifications

- **Redpanda Connect lands gzipped NDJSON, not Parquet.** The open-source
  Redpanda Connect build doesn't ship a Parquet encoder out of the box, so v1
  lands compressed JSON lines instead. The Dagster `landed_events` asset reads
  these files directly (via boto3) and INSERTs into the Iceberg table — Trino
  never has to read the raw JSON directly, so this is an implementation detail
  that can change (e.g. to Parquet via a custom Connect plugin) without
  touching anything downstream.
- **No landing checkpoint/watermark.** `landed_events` reprocesses every
  object under `raw/events/` on each run. This is safe (dbt's `stg_events`
  dedupes by `event_id`) but wasteful once file counts grow — the natural
  follow-up is tracking processed S3 keys (e.g. in a small Postgres table or
  Dagster asset check) once volumes justify it.
- **Nessie runs with an in-memory version store** by default (`.env` /
  `NESSIE_VERSION_STORE_TYPE=IN_MEMORY`) — catalog metadata is lost on
  container recreate. Switch to `JDBC` backed by Postgres before relying on
  this for anything durable.
- **Only `iceberg.marts.curated_events` is embedded**, not raw events — too
  high-volume/low-signal per row for chat-Q&A grain. A daily-rollup mart plus
  a second embedding pass is the natural follow-up for questions spanning
  longer windows.
- **Embeddings are upsert-only.** `curated_events_embeddings` uses a
  deterministic `uuid5(user_id|event_type|event_hour)` point ID so
  re-materializing overwrites stale vectors instead of duplicating them, but
  it does not delete vectors whose source row disappears upstream. A periodic
  full-resync mode is the natural follow-up if the mart's grain changes.
  Embeddings are also computed one row at a time via HTTP calls to Ollama —
  fine at this data volume, batching is the follow-up once row counts grow.
- **`ghcr.io/open-webui/pipelines` has no immutable version tags upstream**
  as of writing, so `:main` is used as a documented exception to the
  "pin every image" convention.
- **The pipelines framework only special-cases `"manifold"`/`"filter"`
  pipeline types in its model listing** — a plain retrieval pipe must NOT set
  `self.type` in `__init__` (see the comment in
  `workload/pipelines/rag_lakehouse_pipeline.py`), or it loads successfully but never
  appears in `/v1/models` / Open WebUI's model dropdown. Also note the
  installed `qdrant-client` (1.18.x) dropped `QdrantClient.search()` in favor
  of `query_points()` — the pipeline uses the latter.
- **Metabase's built-in Trino driver speaks the legacy Presto HTTP protocol**
  (`X-Presto-*` headers, engine name `presto-jdbc`), which recent Trino
  versions reject by default. `config/trino/config.properties` sets
  `protocol.v1.alternate-header-name=Presto` so Trino accepts it. Metabase's
  database connection and starter dashboard are also not file-declarative —
  they're created once via its REST API (see
  `docs/runbooks/phase5-bi-visualization.md`) and then live in the
  `metabase-data` volume, same durability model as `dagster-home`/`qdrant-data`.
- **dbt-trino's generic test macros trip dbt's static SQL parser** ("unable
  to infer all dependencies... typically happens when ref() is placed within
  a conditional block"), so `dbt_project.yml` sets `flags.static_parser:
  false` to force full Jinja-based dependency resolution instead. Without
  this, every dbt test added in Phase 6 fails to compile.
- **`text_to_sql`'s SQL safety guard is a regex/keyword check, not a full SQL
  parser** — appropriate for a local single-user tool, backed by Trino's
  file-based access control as the real enforcement boundary
  (`config/trino/access-control/rules.json` restricts the
  `text_to_sql_readonly` user to read-only on the `iceberg` catalog).
- **Query results must be formatted in plain language before being handed
  back to the LLM for the final answer** — small local models (3B) reliably
  misread raw Python tuple/list output (e.g. read `[(60,)]` as "1 row
  containing the value 60" rather than "60"). `text_to_sql_pipeline.py`'s
  `_format_result` spells results out explicitly to avoid this.
- **The eval harness (`workload/evals/`) is manual-only, no CI exists in this repo
  yet**, and its substring-match assertions for single-digit ground truth
  can false-positive if that digit appears incidentally elsewhere in the
  answer. A GitHub Actions job and stricter answer-extraction are natural
  follow-ups, not built in v1.
- **The backend uses a single shared API key** (`BACKEND_API_KEY` via
  `X-API-Key`), appropriate for a single-user local tool but not safe if
  ever exposed beyond localhost/a trusted LAN — a real session-based auth
  scheme is the natural upgrade for multi-user or remote access.
- **The `/api/trino/query` endpoint's read-only guard is app-level only**
  (same regex/keyword approach as `text_to_sql_pipeline.py`'s guard), not
  backed by a restricted Trino user the way `text_to_sql_readonly` backs
  Phase 7a — the backend currently connects as a normal Trino user with full
  catalog access. Giving it its own read-only Trino user is a documented
  follow-up, not built in v1.
- **The `/api/chat/completions` proxy is non-streaming** — it waits for the
  full pipelines response and returns it in one payload, rather than
  streaming tokens to the frontend. Note streaming (SSE passthrough) as a v2
  follow-up.
- **Frontend config is baked in at Docker build time**, not runtime (a Vite
  requirement — `VITE_*` env vars are compiled into the JS bundle) — changing
  `BACKEND_API_KEY` requires rebuilding the `frontend` image, not just
  restarting the container.
- **The services hub's health checks are a static registry**
  (`backend/app/services_registry.py`), not auto-discovered from the Compose
  files — adding a new service to the platform means adding an entry there
  too. Kept as a deliberately separate endpoint (`/api/services`) from the
  Docker-healthcheck-facing `/api/health` so a dozen extra outbound checks
  can never make the `backend` container itself report unhealthy.

See `docs/scale-out-k3s.md` for the path to a multi-node cluster.
