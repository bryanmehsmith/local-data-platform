import re

# Same pattern as pipelines/text_to_sql_pipeline.py's guard: single top-level
# statement, must start with SELECT/WITH/SHOW/DESCRIBE/EXPLAIN, no
# semicolon-separated second statement, no DDL/DML/admin keywords anywhere.
# App-level only — the real enforcement boundary is Trino's file-based
# access control (config/trino/access-control/rules.json), which now backs
# this endpoint with a dedicated `backend_readonly` Trino user restricted to
# read-only on the iceberg catalog, mirroring the existing
# `text_to_sql_readonly` user used by the pipelines path. This regex guard
# is defense-in-depth on top of that, not the primary boundary.
_ALLOWED_START = re.compile(r"^\s*(SELECT|WITH|SHOW|DESCRIBE|EXPLAIN)\b", re.IGNORECASE)
_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|CALL|COMMENT|USE)\b",
    re.IGNORECASE,
)


class UnsafeQueryError(ValueError):
    pass


def assert_read_only(sql: str) -> None:
    if ";" in sql:
        raise UnsafeQueryError("Multiple statements are not allowed.")
    if not _ALLOWED_START.match(sql):
        raise UnsafeQueryError("Only SELECT/WITH/SHOW/DESCRIBE/EXPLAIN statements are allowed.")
    if _FORBIDDEN.search(sql):
        raise UnsafeQueryError("Query contains a disallowed keyword.")
