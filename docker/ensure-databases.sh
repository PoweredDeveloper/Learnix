#!/usr/bin/env sh
# Ensure application databases exist on Postgres (e.g. old pgdata volume created before init.sql).
# Optionally align the postgres superuser password with docker-compose defaults.
#
# Typical usage from host (repo root, db published on 5433):
#   PGHOST=127.0.0.1 PGPORT=5433 ./docker/ensure-databases.sh
#
# From the Postgres container (official image includes psql):
#   docker compose exec -T db env PGPASSWORD=postgres sh -s < docker/ensure-databases.sh
#
# Environment:
#   PGHOST, PGPORT, PGUSER, PGPASSWORD — libpq / psql (defaults match root docker-compose db service)
#   ENSURE_POSTGRES_PASSWORD=1 — run ALTER USER postgres PASSWORD 'postgres' (use when volume was inited with another password)

set -eu

PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGPASSWORD="${PGPASSWORD:-postgres}"
export PGHOST PGPORT PGUSER PGPASSWORD

if ! command -v psql >/dev/null 2>&1; then
  echo "ensure-databases.sh: psql not found. Install postgresql-client (Debian/Ubuntu) or postgresql16-client (Alpine)." >&2
  exit 1
fi

psql -d postgres -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'sethack') THEN
    CREATE DATABASE sethack;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'sethack_test') THEN
    CREATE DATABASE sethack_test;
  END IF;
END
$$;
SQL

if [ "${ENSURE_POSTGRES_PASSWORD:-}" = "1" ]; then
  echo "ensure-databases.sh: setting postgres user password to match compose default (ENSURE_POSTGRES_PASSWORD=1)."
  psql -d postgres -v ON_ERROR_STOP=1 -c "ALTER USER postgres WITH PASSWORD 'postgres';"
fi

echo "ensure-databases.sh: done (sethack, sethack_test present)."
