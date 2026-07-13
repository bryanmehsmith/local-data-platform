#!/bin/sh
# Idempotent Metabase first-run setup: admin account, Trino database
# connection, and a starter "Curated Events Overview" dashboard.
# Safe to re-run — every step checks for existing state before creating.
set -eu

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/../.env}"

# Read directly out of .env rather than `source`-ing it: admin passwords in
# this project may contain `$` or `#`, which a shell `source` would
# reinterpret (variable/PID expansion, comment-start) and silently corrupt.
env_value() {
  # $1 = key. Takes the first match, strips a trailing CRLF if present.
  grep -m1 "^$1=" "$ENV_FILE" | cut -d= -f2- | tr -d '\r'
}

: "${METABASE_ADMIN_EMAIL:=$(env_value METABASE_ADMIN_EMAIL)}"
: "${METABASE_ADMIN_PASSWORD:=$(env_value METABASE_ADMIN_PASSWORD)}"

METABASE_URL="${METABASE_URL:-http://localhost:3400}"
DB_NAME="Lakehouse (Trino/Iceberg)"
DASHBOARD_NAME="Curated Events Overview"

# Prefer `python3` — the portable, unambiguous name on every Linux distro
# (including WSL). A bare `python` is not guaranteed to exist even when
# python3 does, and on WSL specifically it can resolve via PATH interop to
# the Windows Store's python app-execution-alias stub, which WSL can't
# actually launch (fails with "Permission denied", not "command not found").
PYTHON_BIN=python3
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN=python
fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Neither python3 nor python found on PATH — required for $0." >&2
  echo "(On WSL: sudo apt install python3.)" >&2
  exit 1
fi

echo "Waiting for Metabase to become healthy..."
i=0
until curl -fsS "$METABASE_URL/api/health" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -ge 40 ]; then
    echo "Metabase did not become healthy after $((i * 5))s — aborting." >&2
    exit 1
  fi
  sleep 5
done

json_get() {
  # $1 = python expression fragment applied to json.load(sys.stdin), e.g. "d['setup-token']"
  "$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); print($1)"
}

PROPERTIES=$(curl -fsS "$METABASE_URL/api/session/properties")
HAS_USER=$(echo "$PROPERTIES" | json_get "d.get('has-user-setup', False)")

if [ "$HAS_USER" != "True" ]; then
  # Note: `setup-token` stays populated in /api/session/properties even after
  # setup completes on this Metabase version — `has-user-setup` is the
  # reliable signal, not token presence.
  SETUP_TOKEN=$(echo "$PROPERTIES" | json_get "d.get('setup-token') or ''")
  echo "Metabase not yet initialized — running first-time setup..."
  curl -fsS -X POST "$METABASE_URL/api/setup" -H "Content-Type: application/json" -d "{
    \"token\": \"$SETUP_TOKEN\",
    \"user\": {\"first_name\": \"Admin\", \"last_name\": \"User\", \"email\": \"$METABASE_ADMIN_EMAIL\", \"password\": \"$METABASE_ADMIN_PASSWORD\"},
    \"prefs\": {\"site_name\": \"Local Data Platform\", \"allow_tracking\": false}
  }" >/dev/null
  echo "Admin account created."
else
  echo "Metabase already initialized — skipping setup."
fi

SESSION=$(curl -fsS -X POST "$METABASE_URL/api/session" -H "Content-Type: application/json" \
  -d "{\"username\":\"$METABASE_ADMIN_EMAIL\",\"password\":\"$METABASE_ADMIN_PASSWORD\"}" | json_get "d['id']")

DB_ID=$(curl -fsS "$METABASE_URL/api/database" -H "X-Metabase-Session: $SESSION" \
  | json_get "next((str(x['id']) for x in d['data'] if x['name'] == '$DB_NAME'), '')")

if [ -z "$DB_ID" ]; then
  echo "Creating Trino database connection..."
  DB_ID=$(curl -fsS -X POST "$METABASE_URL/api/database" -H "Content-Type: application/json" -H "X-Metabase-Session: $SESSION" -d '{
    "engine": "presto-jdbc",
    "name": "'"$DB_NAME"'",
    "details": {"host": "trino", "port": 8080, "catalog": "iceberg", "schema": "marts", "user": "metabase", "ssl": false}
  }' | json_get "d['id']")
  echo "Database connection created (id=$DB_ID)."
else
  echo "Trino database connection already exists (id=$DB_ID) — skipping."
fi

DASHBOARD_ID=$(curl -fsS "$METABASE_URL/api/dashboard" -H "X-Metabase-Session: $SESSION" \
  | json_get "next((str(x['id']) for x in d if x['name'] == '$DASHBOARD_NAME'), '')")

if [ -n "$DASHBOARD_ID" ]; then
  # A dashboard can exist with zero cards if a previous run failed partway
  # through (e.g. after creating the dashboard but before adding cards) —
  # check card count, not just dashboard existence, before deciding to skip.
  CARD_COUNT=$(curl -fsS "$METABASE_URL/api/dashboard/$DASHBOARD_ID" -H "X-Metabase-Session: $SESSION" \
    | json_get "len(d['dashcards'])")
  if [ "$CARD_COUNT" -gt 0 ]; then
    echo "Starter dashboard already exists with $CARD_COUNT card(s) (id=$DASHBOARD_ID) — skipping."
    exit 0
  fi
  echo "Starter dashboard exists but has no cards (id=$DASHBOARD_ID) — resuming setup."
fi

echo "Creating starter questions..."

Q1=$(curl -fsS -X POST "$METABASE_URL/api/card" -H "Content-Type: application/json" -H "X-Metabase-Session: $SESSION" -d '{
  "name": "Events per hour by type",
  "dataset_query": {"type": "native", "native": {"query": "SELECT date_trunc('"'"'hour'"'"', event_time) AS hour, event_type, sum(event_count) AS events FROM iceberg.marts.curated_events GROUP BY 1, 2 ORDER BY 1"}, "database": '"$DB_ID"'},
  "display": "bar",
  "visualization_settings": {}
}' | json_get "d['id']")

Q2=$(curl -fsS -X POST "$METABASE_URL/api/card" -H "Content-Type: application/json" -H "X-Metabase-Session: $SESSION" -d '{
  "name": "Top 10 users by volume",
  "dataset_query": {"type": "native", "native": {"query": "SELECT user_id, sum(event_count) AS events FROM iceberg.marts.curated_events GROUP BY 1 ORDER BY 2 DESC LIMIT 10"}, "database": '"$DB_ID"'},
  "display": "bar",
  "visualization_settings": {}
}' | json_get "d['id']")

Q3=$(curl -fsS -X POST "$METABASE_URL/api/card" -H "Content-Type: application/json" -H "X-Metabase-Session: $SESSION" -d '{
  "name": "Total events",
  "dataset_query": {"type": "native", "native": {"query": "SELECT sum(event_count) AS total_events FROM iceberg.marts.curated_events"}, "database": '"$DB_ID"'},
  "display": "scalar",
  "visualization_settings": {}
}' | json_get "d['id']")

if [ -z "$DASHBOARD_ID" ]; then
  DASHBOARD_ID=$(curl -fsS -X POST "$METABASE_URL/api/dashboard" -H "Content-Type: application/json" -H "X-Metabase-Session: $SESSION" -d '{
    "name": "'"$DASHBOARD_NAME"'"
  }' | json_get "d['id']")
fi

# Metabase 0.51's dashcard API is a single batch PUT, not one POST per card
# (a plain POST to this path 404s — "API endpoint does not exist"). Negative
# `id` values mark these as new dashcards being added in this request.
curl -fsS -X PUT "$METABASE_URL/api/dashboard/$DASHBOARD_ID/cards" -H "Content-Type: application/json" -H "X-Metabase-Session: $SESSION" -d "{
  \"cards\": [
    {\"id\": -1, \"card_id\": $Q1, \"col\": 0, \"row\": 0, \"size_x\": 6, \"size_y\": 4},
    {\"id\": -2, \"card_id\": $Q2, \"col\": 6, \"row\": 0, \"size_x\": 6, \"size_y\": 4},
    {\"id\": -3, \"card_id\": $Q3, \"col\": 0, \"row\": 4, \"size_x\": 12, \"size_y\": 2}
  ]
}" >/dev/null

echo "Starter dashboard created (id=$DASHBOARD_ID) with 3 cards."
