# Phase 7 — AI Layer Expansion

Requires Phase 4 (local AI chat/RAG) and Phase 6a (dbt tests/descriptions) running.

## 7a. Text-to-SQL pipeline

Adds `processing/pipelines/text_to_sql_pipeline.py` — the LLM generates a SQL query
against a hardcoded schema description, the pipeline validates and executes
it read-only against Trino, then a second LLM call turns the result into a
natural-language answer.

Two independent safety layers:
1. App-level regex guard (`_is_safe_select` in the pipeline) — rejects
   anything with `;`, requires `SELECT`/`WITH` at the start, blacklists
   DDL/DML keywords.
2. Trino-level guard — `config/trino/access-control.properties` +
   `config/trino/access-control/rules.json` restrict the `text_to_sql_readonly`
   Trino user to read-only on the `iceberg` catalog. This is real
   defense-in-depth: even if the app-level guard were bypassed, this user
   physically cannot run DDL/DML.

### Bring up

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d trino --force-recreate  # picks up access-control mounts
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.ai.yml up -d pipelines --force-recreate
```

### Verify

1. Confirm the readonly Trino user is actually blocked:
   ```bash
   docker exec trino trino --user text_to_sql_readonly --execute "INSERT INTO iceberg.raw.events VALUES ('x', 1, 'click', TIMESTAMP '2026-01-01 00:00:00')"
   ```
   Expect `Access Denied: Cannot insert into table iceberg.raw.events`.
2. `curl http://localhost:9099/v1/models -H "Authorization: Bearer 0p3n-w3bu!"` lists `text_to_sql`.
3. Happy path — ask a real question, cross-check against Trino directly:
   ```bash
   curl http://localhost:9099/v1/chat/completions -H "Content-Type: application/json" \
     -H "Authorization: Bearer 0p3n-w3bu!" \
     -d '{"model": "text_to_sql", "messages": [{"role": "user", "content": "How many distinct users have click events?"}]}'
   docker exec trino trino --execute "SELECT count(distinct user_id) FROM iceberg.staging.stg_events WHERE event_type='click'"
   ```
4. Guard unit check (bypasses LLM non-determinism):
   ```bash
   docker exec pipelines python3 -c "
   import sys; sys.path.insert(0, '/app/pipelines')
   from text_to_sql_pipeline import _is_safe_select
   assert _is_safe_select('SELECT * FROM iceberg.raw.events')
   assert not _is_safe_select('DROP TABLE iceberg.raw.events')
   assert not _is_safe_select('SELECT 1; DROP TABLE iceberg.raw.events')
   print('guard OK')
   "
   ```

## 7b. Richer RAG — embed dbt docs

Adds a sibling Dagster asset `dbt_docs_embeddings` (depends on
`dbt_project_assets`), embedding one fact per dbt model (from
`manifest.json`'s descriptions — populated by Phase 6a) into a **second**
Qdrant collection (`dbt_docs`), via a second `QdrantResource` instance
(`qdrant_docs` in `definitions.py`). `rag_lakehouse_pipeline.py`'s
`_retrieve_context` now searches both collections and labels the results
"Data facts" / "Table documentation".

### Bring up

```bash
docker restart dagster-user-code
docker restart pipelines
```

### Verify

1. Materialize `dbt_docs_embeddings` in the Dagster UI (or the full graph).
2. `curl http://localhost:6333/collections/dbt_docs` → point count matches the number of dbt models (2).
3. Ask a documentation question — should answer from the doc embedding instead of "no matching data":
   ```bash
   curl http://localhost:9099/v1/chat/completions -H "Content-Type: application/json" \
     -H "Authorization: Bearer 0p3n-w3bu!" \
     -d '{"model": "lakehouse_rag", "messages": [{"role": "user", "content": "What does the curated_events table represent?"}]}'
   ```
4. Regression check — re-ask the original Phase 4 value question ("How many click events did user 5 have?") and confirm it still answers correctly from data facts.

## 7c. Eval harness

`processing/evals/rag_eval_cases.yaml` + `processing/evals/run_rag_eval.py` — a lightweight,
manual-only regression check (no CI in this repo yet). Ground truth for
numeric questions is computed live from Trino at eval time, not hardcoded.

### Run

```bash
pip install -r processing/evals/requirements.txt
python processing/evals/run_rag_eval.py
```

### Verify

1. Run against the healthy stack — expect all 4 cases to PASS, exit code 0.
2. Deliberately break something — e.g. set `QDRANT_COLLECTION` in `.env` to a
   nonexistent collection name and recreate `pipelines` — re-run the harness
   and confirm it fails loudly (the pipeline's unhandled Qdrant 404 crashes
   the request, so the harness itself raises a connection error and exits
   non-zero — an even more obvious signal than a graceful FAIL).
3. Revert the `.env` change, recreate `pipelines`, wait for it to report
   healthy, and confirm the harness passes again.

## Known limitations (from what the eval harness actually found)

- **`text_to_sql`'s answer-formatting step originally misread raw Python
  tuple results** (`Rows: [(60,)]` read as "1 row containing 60" instead of
  "60"). Fixed by formatting results in plain language
  (`_format_result` in `text_to_sql_pipeline.py`) before handing them to the
  LLM — a real bug the eval harness caught, not a hypothetical one.
- **A 3B model is not perfectly reliable at exact counting/aggregation.**
  Rephrasing a question (e.g. "across all hours") can make the model
  second-guess a retrieved fact it already has. This is a genuine model-size
  limitation, not a pipeline bug — a bigger chat model (see the GPU runbook,
  `docs/runbooks/phase4-local-ai.md`) would be more reliable here.
- **The eval harness's substring match for single-digit ground truth (e.g.
  `"2"`) can false-positive** if that digit appears incidentally elsewhere in
  the answer (a year, a score). Fine for a lightweight manual check; a
  stricter harness would extract the specific claimed number rather than
  substring-match.

## Doc updates

`docs/architecture.md`'s AI data-flow diagram gets both new branches (SQL
generation → Trino → answer; manifest.json → dbt_docs_embeddings → Qdrant),
plus the limitations above added to "known v1 simplifications".

## Exit criteria

All 4 eval cases pass against the live stack; the readonly Trino user is
provably blocked from writes; a documentation question is answered from the
new `dbt_docs` collection without breaking the original data-fact RAG path.
