# Phase 8 — Observability (Prometheus + Grafana + Loki + Promtail + cAdvisor)

Additive to everything else — no dependency on a specific prior phase beyond
having some services running to observe. One existing-file change is
required: `MINIO_PROMETHEUS_AUTH_TYPE: public` on the `minio` service in
`docker/docker-compose.yml` (already applied), so MinIO's `/minio/v2/metrics/cluster`
endpoint doesn't require a bearer token.

## What's genuinely available (verified, not assumed)

| Service | Native Prometheus metrics? |
|---|---|
| Redpanda | Yes — `/public_metrics` on its admin port (`9644`), no config change needed |
| Qdrant | Yes — `/metrics` on `6333` |
| MinIO | Yes — `/minio/v2/metrics/cluster`, made unauthenticated via the env var above |
| Trino | **No** — metrics live in JMX; would need a JMX Prometheus Java agent bundled into a custom image. Deliberately **not built in v1** (real but nontrivial — bundling a jar and a rules file into a custom Trino image) — a documented stretch goal, not attempted here to avoid a fragile half-implementation. |
| Dagster | **No** native Prometheus integration for service-level metrics. Visibility comes from its logs (via Loki) and container resource usage instead. |
| Ollama | **No** maintained exporter for the pinned version. Same fallback as Dagster. |

cAdvisor gives container-level CPU/mem/network regardless of app-level
metrics — the intended baseline for the two gaps above.

## Bring up

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d minio --force-recreate  # picks up MINIO_PROMETHEUS_AUTH_TYPE
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.observability.yml up -d
```

## Verify

1. All five new containers report healthy: `docker compose -f docker/docker-compose.yml -f docker/docker-compose.observability.yml ps`.
2. Prometheus targets are all `up`: `curl -s http://localhost:9090/api/v1/targets | python -m json.tool`.
3. Native endpoints return real data directly:
   ```bash
   curl -s http://localhost:6333/metrics | head
   curl -s http://localhost:9000/minio/v2/metrics/cluster | head
   docker exec prometheus wget -qO- http://redpanda:9644/public_metrics | head
   ```
4. Grafana (http://localhost:3300, login `admin` / `$GRAFANA_ADMIN_PASSWORD`) has both datasources provisioned (Settings → Data Sources shows Prometheus + Loki) and all three dashboards under Dashboards.
5. Loki has ingested logs from every running container with zero config on
   those services:
   ```bash
   curl -s "http://localhost:3500/loki/api/v1/label/container/values"
   ```
   Cross-check one container's content matches `docker logs`:
   ```bash
   curl -s -G "http://localhost:3500/loki/api/v1/query_range" --data-urlencode 'query={container="minio"}' --data-urlencode 'limit=3'
   docker logs minio --tail 3
   ```
6. **Deliberate failure test:** `docker stop redpanda`; within ~15-20s the
   Prometheus target for `redpanda` flips to `down` (`curl .../api/v1/targets`
   shows `"health":"down"`); `docker start redpanda` and confirm it recovers
   to `up` within a scrape interval.

## Known gap found during verification: cAdvisor per-container metrics

**cAdvisor cannot see individual application containers under this Docker
Desktop for Windows setup.** Its own logs show:

```
Failed to create existing container: ... failed to identify the read-write
layer ID for container "...". - open /rootfs/var/lib/docker/image/overlayfs/
layerdb/mounts/.../mount-id: no such file or directory
```

Only `/docker/buildkit`, `/docker/buildx`, and a couple of system-level
cgroups show up — none of the 20 platform containers. This is a real,
verified incompatibility (not assumed): Docker Desktop's containerd-backed
image store doesn't match the classic dockerd + overlay2 `layerdb` layout
cAdvisor's container-identification code expects. The `cadvisor` Prometheus
target itself is healthy and scrapeable — it's specifically per-container
breakdown that's unavailable here. Root-level metrics (`id="/"`, `id="/docker"`)
still work as a coarse whole-host signal.

**This is a host/Docker-Desktop configuration issue, not a bug in this
repo's config** — revisit if/when running on a native Linux Docker host, or
if Docker Desktop's classic (non-containerd) storage driver becomes
available again. Documented here rather than worked around, per the
project's convention of being honest about what's v1-feasible.

## Doc updates

`docs/architecture.md` gets new component rows, an "Observability" section
describing the metrics/logs data paths, and this cAdvisor limitation added
to "known v1 simplifications".

## Exit criteria

Prometheus shows all five real scrape targets `up`; Grafana's three
dashboards are reachable and the Loki-backed one shows live logs; the
deliberate `docker stop`/`start redpanda` test proves the failure-detection
loop end-to-end.
