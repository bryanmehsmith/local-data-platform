# Scaling Out to Kubernetes (k3s)

This is not a numbered phase in the local build-up (Phases 1-9 all run on a
single Docker Compose host) — it's an orthogonal deployment-target change
you can make at any point once the platform works locally. None of the
tools need to be replaced to go from a single Docker Compose host to a
small multi-node cluster; every component has an official Helm chart or
Operator that speaks the same client API. This is a config/deployment
change, not a pipeline rewrite — but it is real work, not a one-command
migration. This guide is honest about what changes and what's genuinely new
ground.

## Prerequisites

- A k3s cluster (or any conformant Kubernetes — k3s is the lightweight
  reference target since it's the natural next step up from a single
  machine) with `kubectl` and `helm` configured against it.
- **A container registry the cluster can pull from.** Locally, `dagster-user-code`,
  `dagster-webserver`, `dagster-daemon` (built from `workload/dagster_project/Dockerfile`)
  and `backend`/`frontend` (built from `backend/Dockerfile`/`frontend/Dockerfile`)
  are built directly by Docker Compose on the same machine that runs them —
  Kubernetes has no equivalent "build on the node" step. You need to push
  these five images to a registry (Docker Hub, GHCR, a self-hosted
  registry, or your cloud provider's) before any Dagster or app-layer
  workload can schedule. This is new work, not carried over from Compose —
  budget time for setting up CI or a manual `docker build && docker push`
  loop before starting the migration.
- Enough node capacity for the stateful services' storage classes (MinIO,
  Nessie's Postgres, Qdrant, Prometheus/Loki/Grafana all want persistent
  volumes) — confirm your cluster has a default `StorageClass` before
  starting.

## Migration order

**MinIO and Redpanda first** (stateful, highest value from clustering) →
**Nessie + Postgres** (must move off `IN_MEMORY` before clustering — see
below) → **Trino** (compute scale) → **Dagster** (orchestration is fine
single-node for a long time, migrate last among the core services) →
**the AI layer** (GPU scheduling is new ground on k8s, not needed until
you're actually running multi-node inference) → **the app layer**
(backend/frontend — simplest, do last since nothing else depends on it).

## MinIO

Switch from single-node/single-drive to distributed mode using the official
[`minio` Helm chart](https://github.com/minio/minio/tree/master/helm/minio),
with 4+ drives/nodes for erasure coding. The S3 API is unchanged — Trino,
Nessie, and the Dagster `MinioResource` need only an updated endpoint
(replace `http://minio:9000` with the chart's Service DNS name, e.g.
`http://minio.default.svc.cluster.local:9000`).

```bash
helm repo add minio https://charts.min.io/
helm install minio minio/minio \
  --set mode=distributed \
  --set replicas=4 \
  --set persistence.size=50Gi \
  --set rootUser=$MINIO_ROOT_USER,rootPassword=$MINIO_ROOT_PASSWORD
```

Recreate the `warehouse`/`raw` buckets and the app user/policy the same way
`config/minio/init/create-buckets.sh` does locally — either run that script
once against the new endpoint via `mc`, or port it to a Kubernetes `Job`.

## Redpanda

Use the official
[Redpanda Helm chart / Redpanda Operator](https://docs.redpanda.com/current/deploy/deployment-option/self-hosted/kubernetes/)
to scale from 1 to 3+ brokers with rack awareness. The Kafka API is
unchanged, so `workload/sample_producer/produce_events.py`, Redpanda
Connect, and the schema registry client config don't change — only the
broker addresses (update `TRINO_HOST`-style env vars and Redpanda Connect's
`seed_brokers` in `workload/connectors/redpanda-connect/events-to-minio.yaml`
to the new Service DNS name).

```bash
helm repo add redpanda https://charts.redpanda.com
helm install redpanda redpanda/redpanda \
  --set statefulset.replicas=3 \
  --set storage.persistentVolume.size=20Gi
```

## Nessie

**This is where the documented "known v1 simplification" actually gets
resolved**: Nessie's `IN_MEMORY` version store (the local default) loses all
catalog metadata on every restart — acceptable for a single dev machine,
not for a cluster. Before or during this migration, switch
`NESSIE_VERSION_STORE_TYPE` from `IN_MEMORY` to `JDBC`, backed by a real
Postgres (either a small `postgresql` Helm chart release, or a managed
cloud Postgres instance). The REST API Trino/dbt talk to is unchanged —
only the Nessie deployment's own backing store changes.

```bash
helm install nessie-db bitnami/postgresql --set auth.database=nessie
# then deploy Nessie (own chart or a Deployment) with
# nessie.version.store.type=JDBC and the Postgres JDBC URL/credentials
```

## Trino

Use the official
[Trino Helm chart](https://trino.io/docs/current/installation/kubernetes.html)
to split into a coordinator and multiple worker pods. Catalog config
(`config/trino/catalog/iceberg.properties`) is unchanged in content — copy
it into the chart's catalog ConfigMap, updating only the `s3.endpoint` and
`iceberg.nessie-catalog.uri` hostnames to their cluster Service DNS names.
The file-based access control (`config/trino/access-control/`) mounts the
same way, as a ConfigMap volume on the coordinator.

## Dagster

Switch the run launcher to `dagster-k8s` (or `dagster-celery-k8s` for higher
concurrency) via the official
[Dagster Helm chart](https://docs.dagster.io/deployment/guides/kubernetes).
Runs execute as Kubernetes Jobs instead of local subprocesses. Asset code
(`workload/dagster_project/local_data_platform/`) and dbt models
(`workload/dbt_project/`) are unchanged — push the `dagster_project`
image to your registry and point the Helm chart's `dagsterWebserver`/
`dagsterDaemon`/`userCodeDeployments` values at it instead of building
locally.

## The AI layer (Ollama, Qdrant, pipelines, Open WebUI)

**New ground not covered by a simple "same Helm chart" story.** Ollama's
GPU passthrough (`docker/docker-compose.ai.gpu.yml`'s
`deploy.resources.reservations.devices` block) has no direct Compose-to-k8s
translation — on Kubernetes, GPU scheduling means:
- Installing the [NVIDIA device plugin](https://github.com/NVIDIA/k8s-device-plugin)
  on GPU-equipped nodes so they advertise `nvidia.com/gpu` as a schedulable resource.
- Adding `resources.limits: {nvidia.com/gpu: 1}` to the Ollama pod spec, plus
  a `nodeSelector`/toleration if GPU nodes are tainted (common in mixed
  clusters so non-GPU workloads don't land there).
- Ollama itself needs no code change — it auto-detects CUDA the same way it
  does in Docker, this is purely a scheduling/resource-request concern.

Qdrant and the `pipelines` sidecar are stateless/lightweight — plain
Deployments + Services, `pipelines`' `PIPELINES_URLS`/volume-mounted scripts
work identically (mount `workload/pipelines/` as a ConfigMap or bake it
into a custom image if you want immutable deployments instead of the local
hot-reload-via-bind-mount pattern). Open WebUI needs a PVC for
`/app/backend/data` in place of the local `openwebui-data` volume.

## The app layer (backend + frontend)

Simplest migration — plain Deployments + Services + an Ingress
(nginx-ingress or Traefik, whichever k3s ships with by default). The
backend's `DAGSTER_GRAPHQL_URL`/`TRINO_HOST`/`QDRANT_URL`/`PIPELINES_URL`
env vars just need updating to cluster Service DNS names
(`app/config.py`'s defaults are all overridable via env, no code change).
The frontend's `VITE_API_BASE_URL`/`VITE_API_KEY` are baked in at Docker
build time (documented v1 simplification) — rebuild the frontend image
pointing at the Ingress's public URL rather than `localhost:8000`.

## Networking: how the flat Docker network maps to Kubernetes

Locally, every service resolves every other service by its Compose service
name on the single `ldp-net` bridge network (e.g. `http://trino:8080`).
Kubernetes' equivalent is Service DNS: each Helm-installed or
hand-deployed service gets a ClusterIP Service, resolvable as
`<service-name>.<namespace>.svc.cluster.local` (or just `<service-name>`
from within the same namespace). Every config file that currently
hardcodes a bare Compose hostname needs its host updated (not its shape —
the connection strings/API contracts are otherwise identical):

| File | What changes |
|---|---|
| `config/trino/catalog/iceberg.properties` | `s3.endpoint`, `iceberg.nessie-catalog.uri` |
| `backend/app/config.py` | `trino_host`, `dagster_graphql_url`, `qdrant_url`, `ollama_base_url`, `pipelines_url` defaults (all overridable via env — set these as Deployment env vars, no code change) |
| `workload/pipelines/*.py` | Same pattern — `OLLAMA_BASE_URL`/`QDRANT_URL`/`TRINO_HOST` env vars |
| `workload/dagster_project/local_data_platform/workspace.yaml` | gRPC code-server host (`dagster-user-code` → its Service DNS name) |
| `workload/connectors/redpanda-connect/events-to-minio.yaml` | Redpanda `seed_brokers`, MinIO S3 endpoint |

## Explicitly out of scope for this guide

Don't treat the sections above as a complete migration checklist — they
cover "how each service's deployment model changes." Not covered here, and
worth planning separately before doing this for real:
- **Secrets management** — locally everything reads from a single `.env`
  file; on k8s this should become native `Secret` objects (or an external
  secrets manager), not a ConfigMap with plaintext values.
- **Ingress/TLS** — this guide assumes `kubectl port-forward` for
  verification; a real deployment needs proper ingress rules and
  certificates for anything exposed beyond the cluster.
- **Backup/restore strategy for persistent volumes** — MinIO, the Nessie
  Postgres, Qdrant, and the observability stack's volumes all need a real
  backup policy once they're not "just re-run `make up` from scratch" on a
  single dev machine.
- **CI/CD for the five custom images** — the prerequisites section above
  mentions pushing images to a registry; setting up an actual build
  pipeline for that is a separate, follow-up piece of work.

## Verifying parity after migration

Re-run the Phase 1-3 verification steps (`docs/runbooks/`) against the
k3s-hosted endpoints (via `kubectl port-forward` or your Ingress) — same
SQL, same asset graph, same producer script, just pointed at new hostnames.
`kubectl get pods -A` should show all services `Running`. Migrate and
verify one service at a time in the order above rather than attempting a
big-bang cutover — each service's local Compose setup keeps working
independently while others move, since nothing here requires touching more
than one service's config at a time.
