"""Lightweight regression check for the RAG/text-to-SQL pipelines.

Not wired into CI (this repo has no CI pipeline yet) - run manually after any
change to rag_lakehouse_pipeline.py, text_to_sql_pipeline.py, dbt models, or
the embedding assets. A GitHub Actions job that spins up the stack and runs
this script is a natural follow-up once CI is introduced.

Run from the host (pipelines:9099 and trino:8080 are both published to
localhost) or from inside dagster-user-code, which already has `trino` and
`requests` installed:

    docker exec dagster-user-code python -m pip install --quiet PyYAML
    docker exec -w /opt/dagster/app dagster-user-code python evals/run_rag_eval.py
"""

import json
import os
import sys

import requests
import trino
import yaml

PIPELINES_URL = os.environ.get("PIPELINES_URL", "http://localhost:9099/v1/chat/completions")
API_KEY = os.environ.get("OPENWEBUI_PIPELINES_API_KEY", "0p3n-w3bu!")
TRINO_HOST = os.environ.get("TRINO_HOST", "localhost")
TRINO_PORT = int(os.environ.get("TRINO_PORT", "8080"))
TRINO_USER = os.environ.get("TRINO_USER", "eval")
TRINO_CATALOG = os.environ.get("TRINO_CATALOG", "iceberg")

CASES_PATH = os.path.join(os.path.dirname(__file__), "rag_eval_cases.yaml")


def trino_scalar(sql: str):
    conn = trino.dbapi.connect(host=TRINO_HOST, port=TRINO_PORT, user=TRINO_USER, catalog=TRINO_CATALOG)
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchone()[0]


def ask_pipeline(model: str, question: str) -> str:
    resp = requests.post(
        PIPELINES_URL,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": question}]},
        timeout=120,
    )
    resp.raise_for_status()

    # The pipelines sidecar returns Server-Sent Events chunks even for a
    # single non-streamed reply from our Pipeline.pipe() implementations.
    text = resp.text
    if not text.lstrip().startswith("data:"):
        return json.loads(text)["choices"][0]["message"]["content"]

    parts = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:") :].strip()
        if payload == "[DONE]":
            continue
        chunk = json.loads(payload)
        delta = chunk["choices"][0].get("delta", {})
        parts.append(delta.get("content", ""))
    return "".join(parts)


def main() -> None:
    with open(CASES_PATH) as f:
        cases = yaml.safe_load(f)

    passed = failed = 0
    for case in cases:
        answer = ask_pipeline(case["pipeline_model"], case["question"])
        if "ground_truth_sql" in case:
            expected = str(trino_scalar(case["ground_truth_sql"]))
            ok = expected in answer
        elif "expect_not_substring" in case:
            ok = case["expect_not_substring"].lower() not in answer.lower()
        else:
            substrings = case.get("expect_any_substring") or [case["expect_substring"]]
            ok = any(s.lower() in answer.lower() for s in substrings)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['name']}: {answer[:150]!r}")
        passed += int(ok)
        failed += int(not ok)

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
