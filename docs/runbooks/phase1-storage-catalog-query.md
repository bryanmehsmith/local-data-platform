# Phase 1 — Storage + Catalog + Query Engine

Brings up MinIO, Nessie, and Trino only. Proves you can create an Iceberg
table and query it.

Nessie's catalog metadata is stored in a dedicated `nessie-postgres` service
(JDBC version store), not in-memory — `docker compose up nessie` will bring
`nessie-postgres` up automatically first via its `depends_on`, so no separate
step is needed here, but you'll see one extra container in `docker compose ps`.

## Bring up

```bash
cp .env.example .env   # first time only; edit secrets as needed
docker compose --env-file .env -f docker/docker-compose.yml up -d minio minio-init nessie trino
```

Wait for all five containers to report healthy: `docker compose --env-file .env -f docker/docker-compose.yml ps`

## Verify

1. **MinIO console** — http://localhost:9001 (login with `MINIO_ROOT_USER` /
   `MINIO_ROOT_PASSWORD` from `.env`). Confirm the `warehouse` and `raw`
   buckets exist.
2. **Nessie** — `curl http://localhost:19120/api/v2/config` should return a
   JSON config with a `main` default branch.
3. **Create and query an Iceberg table:**
   ```bash
   docker exec -i trino trino < scripts/create_iceberg_table.sql
   ```
   Expected output: a single row `1 | hello iceberg`.
4. **Confirm files landed in MinIO** — in the console, browse
   `warehouse/raw/smoke_test/` and confirm `data/*.parquet` and
   `metadata/*.json` exist.
5. **Confirm Nessie recorded a commit** — `curl http://localhost:19120/api/v2/trees/tree/main`
   should show a non-empty commit hash.

## Exit criteria

A table created via Trino is visible as Iceberg files in MinIO, and the
`main` branch in Nessie shows a commit for it.
