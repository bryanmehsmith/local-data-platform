#!/bin/sh
# Generates /usr/share/nginx/html/config.js at container start from runtime
# env vars, so the same built image can be pointed at different backends
# without rebuilding. Read by index.html before the app bundle loads (see
# frontend/src/api/client.ts, which prefers window.__CONFIG__ over the
# build-time VITE_* fallbacks baked in at `npm run build` time).
set -eu

API_BASE_URL="${API_BASE_URL:-http://localhost:8000/api}"
API_KEY="${API_KEY:-}"

cat <<EOF > /usr/share/nginx/html/config.js
window.__CONFIG__ = { API_BASE_URL: "${API_BASE_URL}", API_KEY: "${API_KEY}" };
EOF
