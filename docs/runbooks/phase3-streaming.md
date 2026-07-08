# Phase 3 — Streaming

Requires Phases 1 and 2 running. Adds Redpanda, Redpanda Console, and
Redpanda Connect, and exercises the `landed_events` Dagster asset.

## Bring up

```bash
docker compose --env-file .env -f docker/docker-compose.yml --profile streaming up -d
```

This starts `redpanda`, `redpanda-console`, and `redpanda-connect` (the
`streaming` Compose profile) in addition to the Phase 1 services.

## Produce sample events

```bash
cd processing/sample_producer
pip install -r requirements.txt
python produce_events.py --count 100 --brokers localhost:19092
```

## Verify

1. **Redpanda Console** — http://localhost:8090. Topic `raw.events` should
   show 100 new messages; preview a few payloads.
2. **Landing** — after ~30s (Redpanda Connect's batch period), check the
   MinIO console `raw` bucket for new objects under
   `events/dt=YYYY-MM-DD/hour=HH/*.json.gz`.
3. **Trigger the landing asset** — either wait for
   `redpanda_landing_sensor` to fire (polls every 30s) or manually
   materialize `landed_events` (and its downstream dbt assets) in the
   Dagster UI.
4. Confirm new rows arrived:
   ```bash
   docker exec -it trino trino --execute "SELECT count(*) FROM iceberg.raw.events"
   docker exec -it trino trino --execute "SELECT count(*) FROM iceberg.marts.curated_events"
   ```
   Both counts should have increased relative to the Phase 2 seed-only state.
5. **Cluster health** — `docker exec -it redpanda rpk cluster health` should
   report healthy with no under-replicated partitions.

## Exit criteria

An event produced by `produce_events.py` is visible end-to-end in
`iceberg.marts.curated_events` after a Dagster run — the full chain
(producer → Redpanda → Connect → raw Iceberg → dbt → curated Iceberg) works.
