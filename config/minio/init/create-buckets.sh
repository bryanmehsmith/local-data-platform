#!/bin/sh
set -eu

mc alias set local http://minio:9000 "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}"

mc mb --ignore-existing local/warehouse
mc mb --ignore-existing local/raw

# App user + credentials that Trino/Nessie/Dagster use instead of root.
# `mc admin user add` sets the secret whether the user is new or already
# exists, so re-running this after rotating MINIO_APP_SECRET_KEY in .env
# actually takes effect instead of silently keeping the old secret.
mc admin user add local "${MINIO_APP_ACCESS_KEY}" "${MINIO_APP_SECRET_KEY}"
mc admin policy attach local readwrite --user "${MINIO_APP_ACCESS_KEY}" || true

echo "MinIO buckets and app user ready."
