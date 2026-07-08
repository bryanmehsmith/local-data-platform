import gzip
import json

from dagster import AssetExecutionContext, asset

from local_data_platform.resources import MinioResource, TrinoResource

RAW_BUCKET = "raw"
RAW_PREFIX = "events/"


@asset(group_name="raw", compute_kind="python", deps=["raw_events_seed"])
def landed_events(context: AssetExecutionContext, minio: MinioResource, trino: TrinoResource) -> None:
    """Reads gzipped NDJSON files landed by Redpanda Connect and inserts them
    into the managed Iceberg table iceberg.raw.events.

    v1 simplification: reprocesses all objects under the prefix on every run
    (no watermark/checkpoint). Downstream dbt staging dedupes by event_id, so
    re-landing the same file is safe but wasteful — a checkpoint keyed on S3
    object key is the natural follow-up once volumes grow.
    """
    rows = []
    keys = list(minio.list_objects(RAW_BUCKET, RAW_PREFIX))
    for key in keys:
        raw_bytes = minio.get_object_bytes(RAW_BUCKET, key)
        text = gzip.decompress(raw_bytes).decode("utf-8")
        for line in text.splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            rows.append(event)

    context.log.info(f"Read {len(rows)} events from {len(keys)} landed files")

    if not rows:
        return

    values = ", ".join(
        "('{event_id}', {user_id}, '{event_type}', TIMESTAMP '{ts}')".format(
            event_id=r["event_id"].replace("'", "''"),
            user_id=int(r["user_id"]),
            event_type=r["event_type"].replace("'", "''"),
            ts=r["ts"].replace("T", " ").split("+")[0].split(".")[0],
        )
        for r in rows
    )
    trino.execute(f"INSERT INTO iceberg.raw.events VALUES {values}")
