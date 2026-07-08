import trino

from app.config import settings


class TrinoClient:
    def get_connection(self):
        return trino.dbapi.connect(
            host=settings.trino_host,
            port=settings.trino_port,
            user=settings.trino_user,
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
