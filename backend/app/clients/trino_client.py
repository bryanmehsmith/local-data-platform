import trino

from app.config import settings


class TrinoClient:
    """Used only by read-only paths (`/api/trino/query`, `/api/trino/tables`,
    `/api/trino/tables/{schema}/{table}/columns`, and the health check's
    `SELECT 1`) — so it connects as the dedicated `trino_readonly_user`,
    which Trino's file-based access control also restricts to read-only
    (see config/trino/access-control/rules.json). If a write-needing path
    is ever added, give it its own connection using `settings.trino_user`
    instead of changing this one.
    """

    def get_connection(self):
        return trino.dbapi.connect(
            host=settings.trino_host,
            port=settings.trino_port,
            user=settings.trino_readonly_user,
            catalog=settings.trino_catalog,
        )

    def execute(self, sql: str, max_rows: int = 1000):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(max_rows)
        truncated = len(rows) == max_rows and cur.fetchone() is not None
        return columns, rows, truncated


trino_client = TrinoClient()
