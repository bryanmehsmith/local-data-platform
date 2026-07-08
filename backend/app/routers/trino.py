from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.clients.trino_client import trino_client
from app.sql_guard import UnsafeQueryError, assert_read_only

router = APIRouter()


class QueryRequest(BaseModel):
    sql: str
    max_rows: int = 1000


class QueryResponse(BaseModel):
    columns: list[str]
    rows: list[list]
    row_count: int
    truncated: bool


@router.post("/query", response_model=QueryResponse)
def run_query(req: QueryRequest):
    try:
        assert_read_only(req.sql)
    except UnsafeQueryError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        columns, rows, truncated = trino_client.execute(req.sql, req.max_rows)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {e}")

    return QueryResponse(
        columns=columns,
        rows=[list(r) for r in rows],
        row_count=len(rows),
        truncated=truncated,
    )


@router.get("/tables")
def list_tables():
    result = {}
    for schema in ("raw", "staging", "marts"):
        _, rows, _ = trino_client.execute(f"SHOW TABLES FROM iceberg.{schema}")
        result[schema] = [r[0] for r in rows]
    return result


@router.get("/tables/{schema}/{table}/columns")
def table_columns(schema: str, table: str):
    if not schema.isidentifier() or not table.isidentifier():
        raise HTTPException(status_code=400, detail="Invalid schema or table name")
    try:
        _, rows, _ = trino_client.execute(f"DESCRIBE iceberg.{schema}.{table}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to describe table: {e}")
    return [{"name": r[0], "type": r[1]} for r in rows]
