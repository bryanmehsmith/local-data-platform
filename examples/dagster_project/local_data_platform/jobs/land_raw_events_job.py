from dagster import AssetSelection, define_asset_job

land_raw_events_job = define_asset_job(
    name="land_raw_events_job",
    selection=AssetSelection.assets("landed_events").downstream(),
)
