from dagster import RunRequest, SensorEvaluationContext, sensor

from local_data_platform.jobs.land_raw_events_job import land_raw_events_job
from local_data_platform.resources.minio_resource import MinioResource

RAW_BUCKET = "raw"
RAW_PREFIX = "events/"


@sensor(job=land_raw_events_job, minimum_interval_seconds=30)
def redpanda_landing_sensor(context: SensorEvaluationContext, minio: MinioResource):
    """Fires a run whenever the set of objects under raw/events/ changes."""
    keys = sorted(minio.list_objects(RAW_BUCKET, RAW_PREFIX))
    cursor = str(len(keys))
    if cursor == context.cursor:
        return

    context.update_cursor(cursor)
    yield RunRequest(run_key=cursor)
