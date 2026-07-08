# Phase 4 — Local AI (Chat + RAG over the Lakehouse)

Requires Phases 1-2 running (Trino + the curated Iceberg marts). Adds
Ollama, Qdrant, the `pipelines` RAG sidecar, and Open WebUI.

## Phase A — Ollama + Open WebUI plain chat

```bash
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.ai.yml \
  up -d ollama qdrant pipelines open-webui
docker exec ollama ollama pull llama3.2:3b
```

Verify:
- `curl http://localhost:11434/api/tags` lists `llama3.2:3b`.
- `curl -s http://localhost:11434/api/chat -d '{"model": "llama3.2:3b", "messages": [{"role": "user", "content": "hello"}], "stream": false}'` returns a completion.
- Open http://localhost:3100, create the local admin account, select the model, and chat.

## Phase B — Qdrant standalone

Already started above. Verify:
```bash
curl http://localhost:6333/healthz
curl -X PUT http://localhost:6333/collections/smoke_test -H "Content-Type: application/json" -d '{"vectors": {"size": 4, "distance": "Cosine"}}'
curl -X PUT http://localhost:6333/collections/smoke_test/points -H "Content-Type: application/json" -d '{"points": [{"id": 1, "vector": [0.1,0.2,0.3,0.4]}]}'
curl -X POST http://localhost:6333/collections/smoke_test/points/search -H "Content-Type: application/json" -d '{"vector": [0.1,0.2,0.3,0.4], "limit": 1}'
curl -X DELETE http://localhost:6333/collections/smoke_test
```

## Phase C — Embedding asset

```bash
docker exec ollama ollama pull nomic-embed-text
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.dagster.yml -f docker/docker-compose.ai.yml \
  up -d --build dagster-user-code dagster-webserver dagster-daemon
```

Materialize `curated_events_embeddings` in the Dagster UI (http://localhost:3000) — it depends on `curated_events`, so run the full asset graph if the lakehouse is empty (see `docs/runbooks/phase2-batch-orchestration.md`).

Verify:
```bash
curl http://localhost:6333/collections/curated_events
```
Point count should match the distinct `(user_id, event_type, event_hour)` rows in `iceberg.marts.curated_events`. Re-materializing should not increase the count (upsert, not duplicate).

## Phase D — End-to-end RAG

The pipeline script (`workload/pipelines/rag_lakehouse_pipeline.py`) is bind-mounted into the `pipelines` container and hot-loads — restart the container after editing it:
```bash
docker restart pipelines
```

Verify it's registered:
```bash
curl http://localhost:9099/v1/models -H "Authorization: Bearer 0p3n-w3bu!"
```
Should list `lakehouse_rag` / "Lakehouse RAG (curated_events)".

Verify a grounded answer:
```bash
curl http://localhost:9099/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 0p3n-w3bu!" \
  -d '{"model": "lakehouse_rag", "messages": [{"role": "user", "content": "How many click events did user 5 have?"}]}'
```
Cross-check against Trino directly:
```bash
docker exec trino trino --execute "SELECT * FROM iceberg.marts.curated_events WHERE user_id = 5 AND event_type = 'click'"
```
The two should agree.

Also confirm graceful fallback:
- An out-of-scope question ("What is the capital of France?") should get a plain "not in this data" answer, not a hallucinated lakehouse fact.
- A question about a user/event combination that doesn't exist should say so rather than inventing a count.

Finally, confirm the same model is selectable in the Open WebUI dropdown at http://localhost:3100 (Open WebUI is configured with `OPENAI_API_BASE_URLS=http://pipelines:9099`, so it calls the identical endpoint verified above).

## Phase E — Optional GPU passthrough

Prerequisites: an NVIDIA GPU, the NVIDIA driver on the host, Docker Desktop's WSL2 GPU support enabled, and `nvidia-container-toolkit` installed in the WSL2 distro.

Bring up with the extra overlay:
```bash
make phase4-gpu
# equivalent to: docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.dagster.yml \
#   -f docker/docker-compose.ai.yml -f docker/docker-compose.ai.gpu.yml up -d --build
```

No image or code change is needed — `ollama/ollama` auto-detects CUDA at
startup. Verify:
```bash
docker exec ollama nvidia-smi
docker logs ollama | grep -i cuda
```
A CUDA-initialization line (instead of a CPU-fallback message) confirms the
GPU is in use; a repeat of the Phase D chat request should feel noticeably
faster.

## Exit criteria

Asking "How many click events did user 5 have?" via Open WebUI, model
`Lakehouse RAG (curated_events)`, returns an answer citing the actual count
from `iceberg.marts.curated_events` — proving Iceberg → Dagster embedding
asset → Qdrant → pipelines retrieval → Ollama chat → Open WebUI is fully
wired.
