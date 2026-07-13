import gzip
import json
import re
from datetime import datetime, timezone

from dagster import AssetExecutionContext, MetadataValue, asset

from local_data_platform.resources import MinioResource, TrinoResource

RAW_BUCKET = "raw"
RAW_PREFIX = "events/"

# How many days of `dt=YYYY-MM-DD` partitions to keep in the checkpoint's
# processed-keys set. This keeps the materialization metadata payload
# bounded as the landing zone grows, at the cost of a trade-off: any file
# whose `dt=` partition falls outside this window is dropped from the
# checkpoint (and, if it lands very late, may be silently reprocessed or
# silently skipped). Downstream dbt staging dedupes by event_id, so
# reprocessing is safe -- this only matters for the rare late-arriving file.
CHECKPOINT_WINDOW_DAYS = 14

_DT_SEGMENT = re.compile(r"dt=(\d{4}-\d{2}-\d{2})")


def _load_checkpoint(context: AssetExecutionContext) -> set[str]:
    """Returns the set of object keys already processed as of the asset's
    most recent materialization, or an empty set if there is no prior
    materialization or no `processed_keys` metadata attached to it."""
    event = context.instance.get_latest_materialization_event(context.asset_key)
    if event is None:
        return set()
    materialization = event.asset_materialization
    if materialization is None:
        return set()
    entry = materialization.metadata.get("processed_keys")
    if entry is None:
        return set()
    try:
        return set(entry.value)
    except (TypeError, AttributeError):
        return set()


def _within_checkpoint_window(key: str, today) -> bool:
    """True if `key`'s `dt=YYYY-MM-DD` path segment is within the trailing
    CHECKPOINT_WINDOW_DAYS days of `today`. Keys with no `dt=` segment are
    kept rather than silently dropped, since we have no date to evaluate."""
    match = _DT_SEGMENT.search(key)
    if not match:
        return True
    dt = datetime.strptime(match.group(1), "%Y-%m-%d").date()
    return (today - dt).days <= CHECKPOINT_WINDOW_DAYS


@asset(group_name="raw", compute_kind="python", deps=["raw_events_seed"])
def landed_events(
    context: AssetExecutionContext, minio: MinioResource, trino: TrinoResource
) -> None:
    """Reads gzipped NDJSON files landed by Redpanda Connect and inserts them
    into the managed Iceberg table iceberg.raw.events.

    Checkpointed by object key: each run loads the `processed_keys`
    metadata recorded on this asset's most recent materialization (via
    `_load_checkpoint`) and only reads/inserts objects not already in that
    set, so re-running the asset no longer re-lands files it already
    processed. The checkpoint set carried forward each run is pruned to
    keys whose `dt=YYYY-MM-DD` partition is within the trailing
    CHECKPOINT_WINDOW_DAYS (14) days -- this bounds the metadata payload but
    means files landing later than that window relative to their own `dt=`
    partition are silently skipped/reprocessed. Downstream dbt staging
    dedupes by event_id, so reprocessing is safe; this is a deliberate
    trade-off for the rare very-late-arriving file.
    """
    all_keys = list(minio.list_objects(RAW_BUCKET, RAW_PREFIX))
    checkpoint = _load_checkpoint(context)
    new_keys = [key for key in all_keys if key not in checkpoint]

    context.log.info(
        f"Listed {len(all_keys)} objects under {RAW_PREFIX}; "
        f"{len(new_keys)} are new since the last checkpoint"
    )

    if not new_keys:
        return

    rows = []
    for key in new_keys:
        raw_bytes = minio.get_object_bytes(RAW_BUCKET, key)
        text = gzip.decompress(raw_bytes).decode("utf-8")
        for line in text.splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            rows.append(event)

    context.log.info(f"Read {len(rows)} events from {len(new_keys)} newly landed files")

    if rows:
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

    today = datetime.now(timezone.utc).date()
    new_checkpoint = {
        key for key in (checkpoint | set(new_keys)) if _within_checkpoint_window(key, today)
    }
    context.add_output_metadata({"processed_keys": MetadataValue.json(sorted(new_checkpoint))})
