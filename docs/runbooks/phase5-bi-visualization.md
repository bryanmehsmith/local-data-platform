# Phase 5 — BI / Visualization (Metabase)

Requires Phase 2 running (Trino + populated `iceberg.marts.curated_events`).

## Bring up

```bash
make phase5
# equivalent to: docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.bi.yml up -d metabase
#                followed by ./scripts/bootstrap-metabase.sh (see "First-time setup" below)
```

Metabase's JVM cold start takes 60-90s — the healthcheck allows up to `5s * 40 = 200s`.

## First-time setup

`make phase5` (and `make up`/`make up-nogpu`) run `scripts/bootstrap-metabase.sh`
automatically after bringing Metabase up — it waits for the health endpoint,
then idempotently creates the admin account (if Metabase hasn't been set up
yet), the Trino database connection, and a starter "Curated Events Overview"
dashboard with three cards (events per hour by type, top 10 users by volume,
total events). Re-running it (e.g. via `make phase5` again) skips whatever
already exists rather than erroring or duplicating — safe to run any number
of times. To run it standalone: `./scripts/bootstrap-metabase.sh` — it reads
`METABASE_ADMIN_EMAIL`/`METABASE_ADMIN_PASSWORD` directly out of `.env`
itself (deliberately not via shell `source`, since an admin password
containing `$` or `#` would be corrupted by shell reinterpretation).

**Gotcha:** Metabase's built-in Trino driver is registered under the engine name `presto-jdbc` (it's Metabase's legacy Presto JDBC driver, still protocol-compatible with Trino) — using `"presto"` as the engine name fails with "value must be a valid database engine". It also speaks the legacy `X-Presto-*` HTTP headers rather than `X-Trino-*`, which recent Trino versions reject by default with `Authentication failed: Unauthorized`. Fixed by adding `protocol.v1.alternate-header-name=Presto` to `config/trino/config.properties` (already applied) and restarting Trino.

## Build the starter dashboard

Already handled by `scripts/bootstrap-metabase.sh` (see above) — it creates
all three native-SQL questions (events per hour by type, top 10 users by
volume, total events) and lays them out on the "Curated Events Overview"
dashboard. To customize further, or add more questions, use the Admin UI at
http://localhost:3400 — "New → Question → Native query", then edit the
dashboard.

## Verify

1. `curl -f http://localhost:3400/api/health` → `{"status":"ok"}`.
2. Dashboard "Curated Events Overview" loads with all three cards rendering data.
3. Cross-check the total-events scalar card against Trino directly:
   ```bash
   docker exec trino trino --execute "SELECT sum(event_count) FROM iceberg.marts.curated_events"
   ```
   The two numbers must match exactly.

## Exit criteria

The "Curated Events Overview" dashboard is reachable at http://localhost:3400, all three cards render without error, and the total-events number matches a direct Trino query — proving Metabase reads the same lakehouse data the RAG/text-to-SQL layers use, just through a dashboard instead of chat.
