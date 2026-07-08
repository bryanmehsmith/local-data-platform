#!/bin/sh
# Basic health check across Phase 1 services.
set -eu

echo "MinIO:"; curl -fsS http://localhost:9000/minio/health/live && echo " OK"
echo "Nessie:"; curl -fsS http://localhost:19120/api/v2/config && echo " OK"
echo "Trino:"; curl -fsS http://localhost:8080/v1/info && echo " OK"
