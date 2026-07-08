-- Phase 1 smoke test: run via `docker exec -i trino trino < scripts/create_iceberg_table.sql`
CREATE SCHEMA IF NOT EXISTS iceberg.raw WITH (location = 's3://warehouse/raw');

CREATE TABLE IF NOT EXISTS iceberg.raw.smoke_test (
    id INTEGER,
    msg VARCHAR
) WITH (format = 'PARQUET');

INSERT INTO iceberg.raw.smoke_test VALUES (1, 'hello iceberg');

SELECT * FROM iceberg.raw.smoke_test;
