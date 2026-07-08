from dagster import AssetExecutionContext, asset

from local_data_platform.resources import TrinoResource
from .landing import landed_events

__all__ = ["raw_events_seed", "landed_events"]

RAW_EVENTS_DDL = """
CREATE SCHEMA IF NOT EXISTS iceberg.raw WITH (location = 's3://warehouse/raw');

CREATE TABLE IF NOT EXISTS iceberg.raw.events (
    event_id VARCHAR,
    user_id INTEGER,
    event_type VARCHAR,
    ts TIMESTAMP(6)
) WITH (format = 'PARQUET');
"""


@asset(group_name="raw", compute_kind="trino")
def raw_events_seed(context: AssetExecutionContext, trino: TrinoResource) -> None:
    """Seeds iceberg.raw.events with sample rows to prove the batch path end-to-end.

    Phase 3 replaces/augments this with a landing asset that merges data from
    Redpanda Connect's Parquet drops instead of hardcoded seed rows.
    """
    for stmt in [s.strip() for s in RAW_EVENTS_DDL.split(";") if s.strip()]:
        trino.execute(stmt)

    trino.execute(
        """
        INSERT INTO iceberg.raw.events VALUES
            ('seed-1', 1, 'click', TIMESTAMP '2026-01-01 00:00:00'),
            ('seed-2', 2, 'view',  TIMESTAMP '2026-01-01 00:01:00'),
            ('seed-3', 1, 'click', TIMESTAMP '2026-01-01 00:02:00')
        """
    )
    context.log.info("Seeded iceberg.raw.events")
