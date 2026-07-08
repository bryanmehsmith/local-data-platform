# Phase 2 — Batch Orchestration (Dagster + dbt)

Requires Phase 1 running. Adds Dagster and dbt on top.

## Bring up

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d minio minio-init nessie trino
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.dagster.yml up -d --build
```

## Verify

1. `docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.dagster.yml ps`
   — `dagster-user-code`, `dagster-webserver`, `dagster-daemon` all running.
2. Open the Dagster UI: http://localhost:3000. The asset graph should show
   `raw_events_seed` → `landed_events` → dbt's `stg_events` → `curated_events`.
3. Materialize the full asset graph (select all, click "Materialize all").
   From the CLI you can instead run, inside the `dagster-user-code`
   container: `dagster asset materialize -m local_data_platform.definitions --select '*'`.
4. All three assets should turn green; the dbt asset's run logs (visible in
   the Dagster run view) should show `Completed successfully`.
5. Query the result via Trino:
   ```bash
   docker exec -it trino trino --execute "SELECT count(*) FROM iceberg.marts.curated_events"
   ```
   Should return a non-zero count.

## Exit criteria

Dagster UI shows a green run across the full asset lineage, and
`iceberg.marts.curated_events` is queryable via Trino with the expected
aggregated rows.
