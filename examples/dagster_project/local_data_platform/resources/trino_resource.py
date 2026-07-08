import os

import trino
from dagster import ConfigurableResource


class TrinoResource(ConfigurableResource):
    host: str = "trino"
    port: int = 8080
    user: str = "dagster"
    catalog: str = "iceberg"

    def get_connection(self):
        return trino.dbapi.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            catalog=self.catalog,
        )

    def execute(self, sql: str):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(sql)
        try:
            return cur.fetchall()
        except Exception:
            return None
