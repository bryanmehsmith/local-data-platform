# Phase 6 — Data Quality & Governance

Requires Phase 2 running (Dagster + dbt).

## 6a. dbt tests

`dagster-dbt`'s `@dbt_assets` decorator already runs `dbt build` (see
`workload/dagster_project/local_data_platform/assets/dbt_assets.py`), which runs tests
automatically — no code change needed, only new YAML:

- `workload/dbt_project/models/staging/sources.yml` — `not_null` on `raw.events` columns.
- `workload/dbt_project/models/staging/schema.yml` (new) — `unique`+`not_null` on `stg_events.event_id`, `not_null` on the rest, plus descriptions.
- `workload/dbt_project/models/marts/schema.yml` (new) — `not_null` on all `curated_events` columns, plus a `relationships` test (`curated_events.user_id → stg_events.user_id`).

**Gotcha:** dbt-trino's generic test macros trip dbt's static SQL parser
("dbt was unable to infer all dependencies... typically happens when ref()
is placed within a conditional block"), causing `dbt build` to fail on any
of these tests even though the YAML is correct. Fixed by adding
`flags: { static_parser: false }` to `dbt_project.yml`, which forces full
Jinja rendering for dependency resolution instead of static analysis.

Also note: dbt 1.8+ wants generic test arguments (e.g. `relationships`'s
`to`/`field`) nested under an `arguments:` key, not flat — flat args still
parse but emit a `MissingArgumentsPropertyInGenericTestDeprecation` warning.

### Bring up / apply

```bash
docker restart dagster-user-code   # re-runs `dbt parse` on startup, picks up new schema.yml files
```

### Verify

1. Materialize the full asset graph (Dagster UI at :3000, or
   `dagster asset materialize -m local_data_platform.definitions --select '*'`
   inside `dagster-user-code`) — expect `dbt build` to report 16 PASS (2
   models + 14 tests).
2. Open the `stg_events`/`curated_events` assets in the Dagster UI asset
   catalog → "Checks" tab → confirm each test appears as a green check.
3. **Deliberate failure test:** temporarily break the `relationships` test's
   `field:` in `workload/dbt_project/models/marts/schema.yml` to a nonexistent
   column, restart `dagster-user-code`, re-materialize — confirm dbt reports
   a `Database Error` / `COLUMN_NOT_FOUND` and the Dagster run fails. Revert
   the change and re-materialize to confirm it goes back to green.

## 6b. dbt docs (catalog/lineage)

**Decision: no dedicated catalog tool (OpenMetadata/DataHub/Amundsen all
realistically need 4-6 containers — a metadata DB, a search index, a
scheduler, the app itself) — disproportionate for two dbt models.** Instead,
serve `dbt docs generate`'s static output (searchable docs + lineage DAG +
column descriptions, using the descriptions added in 6a) via a plain nginx
container, and rely on Nessie's existing commit-log UI (`:19120`) for
table-level history.

### Bring up

```bash
docker exec dagster-user-code sh -c "cd dbt_project && dbt docs generate --profiles-dir ."
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.docs.yml up -d dbt-docs
```

Re-run the `dbt docs generate` command any time models/descriptions change — `dbt-docs` just serves whatever is in `workload/dbt_project/target/`, no rebuild needed.

### Verify

1. `curl -f http://localhost:8070/index.html` → 200.
2. Open http://localhost:8070 — confirm `stg_events`/`curated_events` show the descriptions from 6a's `schema.yml` files, and the lineage graph shows `raw.events (source) → stg_events → curated_events`.

## Revisit trigger

Once there are many more models, multiple non-Trino data sources, or a
second engineer who needs search/ownership/tagging across systems,
OpenMetadata's footprint becomes justified — revisit at that point rather
than paying the cost now for two models.

## Exit criteria

All 16 dbt tests pass and show as green asset checks in the Dagster UI, a
deliberately broken test correctly fails, and the dbt-docs site at
`:8070` shows correct descriptions and lineage for both models.
