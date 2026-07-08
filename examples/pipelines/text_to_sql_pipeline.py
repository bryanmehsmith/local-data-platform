"""
title: Lakehouse Text-to-SQL
author: local-data-platform
description: Generates and executes read-only Trino SQL against the Iceberg lakehouse to answer open-ended questions.
requirements: trino, requests
"""

import os
import re
from typing import Generator, Iterator, List, Union

import requests
import trino
from pydantic import BaseModel

SCHEMA_DOC = """
iceberg.raw.events(event_id, user_id, event_type, ts) -- raw, undeduplicated events
iceberg.staging.stg_events(event_id, user_id, event_type, ts) -- deduplicated events, one row per event_id
iceberg.marts.curated_events(user_id, event_type, event_hour, event_count) -- hourly aggregate counts
"""

# Single top-level statement, must start with SELECT or WITH, no semicolon-separated
# second statement, and no DDL/DML/admin keywords anywhere in the string. This is a
# deliberately simple regex/keyword guard (not a full SQL parser) — appropriate for a
# local, single-user tool. Trino's file-based access control (config/trino/access-
# control/rules.json) backs this up: the "text_to_sql_readonly" user is restricted to
# read-only on the iceberg catalog regardless of what SQL this guard lets through.
_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|CALL|COMMENT|USE)\b",
    re.IGNORECASE,
)


def _extract_sql(text: str) -> str:
    m = re.search(r"```sql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip(";")
    # No closing fence (e.g. the model's output got truncated before it closed
    # the block) - strip a lone opening fence so it doesn't get mistaken for
    # part of the SQL and fail the SELECT/WITH check below.
    text = re.sub(r"^\s*```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    return text.strip().rstrip(";")


def _format_result(cols: list, rows: list) -> str:
    # Small local models reliably misread Python repr (e.g. "Rows: [(60,)]" gets
    # read as "1 row containing 60" instead of "the value is 60") — spell the
    # result out in plain language instead of handing over a data structure.
    if len(rows) == 1 and len(cols) == 1:
        return f"The query returned a single value: {cols[0]} = {rows[0][0]}"
    lines = [", ".join(f"{c}={v}" for c, v in zip(cols, row)) for row in rows]
    return f"The query returned {len(rows)} row(s):\n" + "\n".join(lines)


def _is_safe_select(sql: str) -> bool:
    if ";" in sql:  # reject any statement separator — one query only
        return False
    if not re.match(r"^\s*(SELECT|WITH)\b", sql, re.IGNORECASE):
        return False
    if _FORBIDDEN.search(sql):
        return False
    return True


class Pipeline:
    class Valves(BaseModel):
        OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
        OLLAMA_CHAT_MODEL: str = os.environ.get("OLLAMA_CHAT_MODEL", "llama3.2:3b")
        TRINO_HOST: str = os.environ.get("TRINO_HOST", "trino")
        TRINO_PORT: int = int(os.environ.get("TRINO_PORT", "8080"))
        TRINO_USER: str = os.environ.get("TRINO_READONLY_USER", "text_to_sql_readonly")
        TRINO_CATALOG: str = os.environ.get("TRINO_CATALOG", "iceberg")
        MAX_ROWS: int = 50

    def __init__(self):
        # See rag_lakehouse_pipeline.py's comment: do NOT set self.type here,
        # or this pipeline becomes invisible in /v1/models despite loading fine.
        self.id = "text_to_sql"
        self.name = "Lakehouse Text-to-SQL"
        self.valves = self.Valves()

    async def on_startup(self):
        pass

    async def on_shutdown(self):
        pass

    def _chat(self, prompt: str) -> str:
        resp = requests.post(
            f"{self.valves.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": self.valves.OLLAMA_CHAT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def _run_sql(self, sql: str):
        conn = trino.dbapi.connect(
            host=self.valves.TRINO_HOST,
            port=self.valves.TRINO_PORT,
            user=self.valves.TRINO_USER,
            catalog=self.valves.TRINO_CATALOG,
        )
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(self.valves.MAX_ROWS)
        return cols, rows

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        gen_prompt = (
            "You write Trino SQL for a lakehouse with this schema:\n"
            f"{SCHEMA_DOC}\n"
            "Respond with ONLY a single read-only SELECT query in a ```sql code block. "
            "No INSERT/UPDATE/DELETE/DDL. No explanation.\n\n"
            f"Question: {user_message}"
        )
        raw_sql_response = self._chat(gen_prompt)
        sql = _extract_sql(raw_sql_response)

        if not _is_safe_select(sql):
            return (
                "I can only run read-only SELECT queries, and the generated query didn't "
                f"pass that check. Generated query was:\n```sql\n{sql}\n```"
            )

        try:
            cols, rows = self._run_sql(sql)
        except Exception as e:
            return f"The generated query failed to execute against Trino: {e}\n```sql\n{sql}\n```"

        result_text = _format_result(cols, rows)
        answer_prompt = (
            f"Question: {user_message}\n\nSQL used: {sql}\n\nQuery result:\n{result_text}\n\n"
            "Answer the question in plain language using only this result."
        )
        return self._chat(answer_prompt)
