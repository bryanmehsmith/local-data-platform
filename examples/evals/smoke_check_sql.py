"""CI smoke check: confirm every `ground_truth_sql` in rag_eval_cases.yaml still
executes against Trino without error.

Cheaper than the full RAG/text-to-SQL eval (run_rag_eval.py) — needs no LLM,
just the Phase 1+2 containers the dbt-tests CI job already brings up. Catches
schema drift (e.g. a renamed curated column/table) that would otherwise only
surface when someone runs the full eval manually.
"""

import os
import sys

import trino
import yaml

TRINO_HOST = os.environ.get("TRINO_HOST", "localhost")
TRINO_PORT = int(os.environ.get("TRINO_PORT", "8080"))
TRINO_USER = os.environ.get("TRINO_USER", "eval")
TRINO_CATALOG = os.environ.get("TRINO_CATALOG", "iceberg")

CASES_PATH = os.path.join(os.path.dirname(__file__), "rag_eval_cases.yaml")


def main() -> None:
    with open(CASES_PATH) as f:
        cases = yaml.safe_load(f)

    conn = trino.dbapi.connect(
        host=TRINO_HOST, port=TRINO_PORT, user=TRINO_USER, catalog=TRINO_CATALOG
    )
    cur = conn.cursor()

    checked = failed = 0
    for case in cases:
        sql = case.get("ground_truth_sql")
        if not sql:
            continue
        checked += 1
        try:
            cur.execute(sql)
            cur.fetchone()
            print(f"[OK] {case['name']}")
        except Exception as exc:  # noqa: BLE001 - report and keep checking the rest
            failed += 1
            print(f"[FAIL] {case['name']}: {exc}")

    print(f"\n{checked - failed}/{checked} ground_truth_sql cases executed cleanly")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
