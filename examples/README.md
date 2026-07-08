# Examples (bundled reference scenario)

This is the **bundled example** — tracked directly in the infra repo so a
fresh clone works out of the box. It's a synthetic clickstream/events
scenario: Dagster assets and jobs, dbt models, the RAG/text-to-SQL
pipelines, the sample event producer, the Redpanda Connect pipeline config,
the eval harness, and example scenario-specific backend/frontend
extensions.

## How this connects to `workload/`

`workload/` (gitignored, not tracked here) is where Docker Compose,
`backend/app/plugin_loader.py`, and `frontend/src/routes-manifest.ts`
actually look at runtime/build-time — see `docs/architecture.md` and
`workload/README.md`. `make init-workload` (a prerequisite of `phase2`,
`phase3`, and `phase9`) copies this folder's contents into `workload/`
(no-clobber) whenever `workload/dagster_project` doesn't exist yet, so
`make up` works immediately for anyone who clones just the infra repo. If
you check out your own private repo at `workload/` instead and populate
`dagster_project` there, this copy step skips entirely — your content
takes over and this folder's content is simply not used at that point.

## Why the infra repo ships this

Docker Compose files, service config (Trino catalogs, MinIO buckets,
observability dashboards), and the FastAPI/React app layer don't know or
care what data they're processing — but a platform with nothing running on
it isn't a useful thing to clone and try. This example proves every piece
fits together end-to-end and gives a concrete pattern to copy from.

## Contents

- `dagster_project/` — Dagster code location: resource wrappers
  (`TrinoResource`, `MinioResource`, `OllamaResource`, `QdrantResource`,
  `dbt_resource.py`), plus the example's assets, jobs, sensors, and
  `definitions.py`. The generic resource wrappers live here (not in the
  infra repo's own tree) because Dagster's single-code-location model
  doesn't support splitting one Python package across two repos.
- `dbt_project/` — staging/marts models, tests, and dbt docs for the
  example's `curated_events` table.
- `pipelines/` — the `open-webui/pipelines` sidecar's RAG and text-to-SQL
  pipeline implementations.
- `sample_producer/` — a small script that produces synthetic events onto
  Redpanda for the example pipeline to consume.
- `connectors/` — Redpanda Connect pipeline config landing events into
  MinIO as Iceberg-ready files.
- `evals/` — a manual regression harness for the two RAG/text-to-SQL
  pipelines.
- `backend/` — an example scenario-specific FastAPI router
  (`example_plugin.py`), auto-mounted onto the backend at startup. See
  "Extending the app layer" below.
- `frontend/src/routes/` — an example scenario-specific page
  (`ExamplePage.tsx`), auto-registered into the frontend router and sidebar
  nav at build time. See "Extending the app layer" below.

## Extending the app layer

`backend/` and `frontend/` demonstrate the **extension point** a real
workload uses to add scenario-specific routes/pages on top of the reusable
FastAPI/React app layer, without forking or modifying core `backend/`/
`frontend/` code.

**Backend** (`backend/*.py`): each file is loaded by the infra repo's
`backend/app/plugin_loader.py` at startup (bind-mounted in from
`workload/backend`, read-only) and any module-level `router: APIRouter` it
exports gets mounted onto the running app. Default prefix is
`/api/workload/<filename>`; override via a module-level `prefix`. Routes
require the same shared `X-API-Key` as core routes unless the module sets
`require_auth = False`. A broken plugin file is logged and skipped, not
fatal. Edit → restart the `backend` container to pick up changes (no
rebuild needed). See `backend/example_plugin.py`.

**Frontend** (`frontend/src/routes/*.tsx`): each file is discovered at
*build time* by the infra repo's `frontend/src/routes-manifest.ts` (Vite's
`import.meta.glob`, since the frontend is a static build with no runtime
plugin loading) and registered into the app's router and sidebar nav.
Default-export the page component, named-export a `routeMeta` descriptor
(`path`, `label`, `icon`, optional `end`). Requires rebuilding the
`frontend` image to pick up changes (`docker compose ... up -d --build
frontend`). See `frontend/src/routes/ExamplePage.tsx`.

Both examples are templates — copy, rename, and replace with your own in
your private `workload/` repo; delete them once you no longer need the
example.
