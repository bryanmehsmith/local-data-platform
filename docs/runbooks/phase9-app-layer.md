# Phase 9 — Application Layer (FastAPI backend + React/Vite frontend)

Not a fixed-purpose UI — a small backend exposing the platform's primitives
(Trino, Dagster, chat, vector search) as a clean REST API, plus a frontend
scaffold proving each endpoint out with one page. Meant to be extended.

Requires Phase 2 (Trino) at minimum; Phase 4 (Ollama/pipelines/Qdrant) for
the chat/search pages to return real data.

## Bring up

```bash
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.dagster.yml -f docker/docker-compose.app.yml up -d --build
```

## Phase F1 — Backend skeleton + `/query`

`backend/` is a FastAPI app (`app/main.py`), with thin client wrappers in
`app/clients/` mirroring the Dagster resource style (`TrinoClient`,
`DagsterClient`, `PipelinesClient`, `SearchClient`). Auth is a single shared
`BACKEND_API_KEY` via the `X-API-Key` header (all routers except `/api/health`).
The SQL safety guard (`app/sql_guard.py`) mirrors the same
regex/keyword-based approach as `workload/pipelines/text_to_sql_pipeline.py`'s guard —
app-level only, not a substitute for real Trino-side access control.

**Deliberate packaging deviation from `dagster_project`:** the backend uses
only `pyproject.toml`, no `setup.py` — it's a deployable app, not a library,
so the dual-file pattern `dagster_project` uses isn't needed here.

Verify:
```bash
curl -f http://localhost:8000/api/health
curl -H "X-API-Key: $BACKEND_API_KEY" -X POST http://localhost:8000/api/trino/query \
  -H "Content-Type: application/json" -d '{"sql": "SELECT * FROM iceberg.marts.curated_events LIMIT 5"}'
# confirm a write is rejected:
curl -H "X-API-Key: $BACKEND_API_KEY" -X POST http://localhost:8000/api/trino/query \
  -H "Content-Type: application/json" -d '{"sql": "DROP TABLE iceberg.raw.events"}'
# expect 400
# confirm missing key is rejected:
curl -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/trino/query \
  -H "Content-Type: application/json" -d '{"sql": "SELECT 1"}'
# expect 401
```

## Phase F2 — Dagster status/trigger endpoints

**The exact GraphQL mutation shape was verified live against the running
Dagster instance before writing `dagster_client.py`** (Dagster's GraphQL
schema shifts across releases — don't trust remembered field names). Key
findings, baked into `dagster_client.py` as constants:
`repositoryName="__repository__"`, `repositoryLocationName="local_data_platform"`,
`jobName="__ASSET_JOB"`, and materializing a specific asset means passing
`assetSelection: [{path: [...]}]` inside `ExecutionParams.selector`.

Verify:
```bash
curl -H "X-API-Key: $BACKEND_API_KEY" http://localhost:8000/api/dagster/assets
curl -H "X-API-Key: $BACKEND_API_KEY" -X POST http://localhost:8000/api/dagster/assets/raw_events_seed/materialize
curl -H "X-API-Key: $BACKEND_API_KEY" http://localhost:8000/api/dagster/runs/<run_id>
```
Cross-check the run reaches `SUCCESS` and matches what the Dagster UI (:3000) shows.

## Phase F3 — `/chat` + `/search`

`chat.py` proxies to whichever pipelines model is requested (`lakehouse_rag`
or Phase 7's `text_to_sql`), parsing the pipelines sidecar's SSE-chunked
response format (same parsing logic as `workload/evals/run_rag_eval.py`). `search.py`
embeds via Ollama and searches Qdrant directly.

Verify:
```bash
curl -H "X-API-Key: $BACKEND_API_KEY" -X POST http://localhost:8000/api/chat/completions \
  -H "Content-Type: application/json" -d '{"message": "How many click events did user 5 have?"}'
curl -H "X-API-Key: $BACKEND_API_KEY" http://localhost:8000/api/chat/models
curl -H "X-API-Key: $BACKEND_API_KEY" -X POST http://localhost:8000/api/search/query \
  -H "Content-Type: application/json" -d '{"text": "user 5 clicks", "top_k": 3}'
```

## Phase F4 — Frontend scaffold + pages

`frontend/` is a React + Vite SPA (`react-router-dom` + `@tanstack/react-query`,
styled with Tailwind CSS + a small custom component set in
`src/components/ui/`). Five pages, each a thin proof of one backend router:
`QueryPage` (SQL runner + schema/table browser), `AssetsPage`
(list/materialize/poll), `ChatPage`, `SearchPage`, `ServicesPage`. Built via
a multi-stage Dockerfile (`node:20-slim` build → `nginx:1.27-alpine` static
serve with an SPA `try_files` fallback for client-side routing).
`VITE_API_BASE_URL`/`VITE_API_KEY` are baked in at **build time** (Vite
requirement) via Docker build args — changing `BACKEND_API_KEY` in `.env`
requires `--build` on the frontend, same operational pattern as
`dagster-user-code` needing `--build` after code changes.

### Schema/table browser (QueryPage)

`components/SchemaBrowser.tsx` calls `GET /api/trino/tables` (schema → table
list) and, per-table on expand, `GET /api/trino/tables/{schema}/{table}/columns`
(new — runs `DESCRIBE iceberg.{schema}.{table}` via the existing
`trino_client`). Clicking a table's preview icon fills the SQL editor with
`SELECT * FROM iceberg.{schema}.{table} LIMIT 50` and runs it through the
same `/api/trino/query` mutation as manually-typed SQL.

### Services hub (ServicesPage)

`app/services_registry.py` holds static metadata (internal check URL +
external browser URL) for every platform service; `GET /api/services` checks
each with a 2s timeout and returns live status. **Deliberately a separate
endpoint from `/api/health`** — folding a dozen more outbound checks into the
Docker healthcheck endpoint risks the exact hang/false-unhealthy failure
mode already seen once when dependent containers were down (see "known v1
simplifications" in `docs/architecture.md`). `ServicesPage` renders these
grouped by category with a status dot and an "Open ↗" link to each service's
own UI — MinIO, Nessie, Trino, Dagster, Redpanda Console, Open WebUI,
Ollama, Qdrant, pipelines, Metabase, dbt docs, Grafana, Prometheus, cAdvisor
all already have first-class UIs, so this hub links out rather than
reimplementing them.

Verify (HTTP-level — visually confirming the rendered UI requires opening a
browser, which this runbook can't do for you):
```bash
curl -o /dev/null -w "%{http_code}\n" http://localhost:3200/          # 200
curl -o /dev/null -w "%{http_code}\n" http://localhost:3200/query     # 200 (SPA fallback)
curl -i -X OPTIONS http://localhost:8000/api/trino/query \
  -H "Origin: http://localhost:3200" -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: X-API-Key,Content-Type"
# expect access-control-allow-origin: http://localhost:3200
```
Then open http://localhost:3200 in a browser and manually exercise all five
pages — run a query, browse schemas/tables and preview one, materialize an
asset and watch its status poll to `SUCCESS`, send a chat message, run a
search, and check the Services page shows all services healthy with working
"Open" links.

## Phase F5 — Workload extension point

The `workload/backend/`/`workload/frontend/` folders (see
`examples/README.md`'s "Extending the app layer" — `workload/` is seeded
from `examples/` by `make init-workload` on a fresh clone) let
scenario-specific routes/pages get picked up by this same running app
without touching core `backend/`/`frontend/` code.
`workload/backend/example_plugin.py` and
`workload/frontend/src/routes/ExamplePage.tsx` are working templates,
already wired in by default.

### Verify

```bash
curl -H "X-API-Key: $BACKEND_API_KEY" http://localhost:8000/api/workload/example_plugin/example
# expect {"message": "Hello from the workload backend plugin."}
```
Then open http://localhost:3200 — a "Workload Example" nav item should
appear (contributed by `ExamplePage.tsx`, not hand-added to `Sidebar.tsx`)
and render its page correctly at `/workload-example`.

To confirm the mechanism is genuinely additive (not silently hardcoded):
delete or rename both example files, restart the `backend` container and
rebuild the `frontend` image, and confirm the route and nav item both
cleanly disappear.

## Exit criteria

All backend endpoint groups (health, trino incl. table/column browsing,
dagster, chat, search, services) respond correctly against the live stack;
the frontend is served at `:3200` with working CORS and SPA routing; a
browser walkthrough of all five pages round-trips through the backend to
Trino/Dagster/pipelines/Qdrant; the workload example plugin route and page
are both reachable, proving the extension mechanism works end-to-end.
