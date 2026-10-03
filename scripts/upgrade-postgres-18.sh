#!/bin/sh
# Migrate an existing PostgreSQL 17 database (volume "postgres-data") to the
# PostgreSQL 18 service (volume "postgres18-data") of this compose project.
#
# Why not just bump the image: a major version cannot open the previous
# version's data directory, and the official image expects its volume at
# /var/lib/postgresql since 18 instead of /var/lib/postgresql/data.
#
# Dump/restore instead of pg_upgrade: pg_upgrade needs the binaries of both
# major versions in one container, which the official images do not ship.
# For a Hibiscus database this takes seconds.
#
# Safe to re-run. The old volume is left untouched as a backup; remove it
# yourself once Hibiscus works:  docker volume rm <project>_postgres-data
#
# Usage (from the repository directory, with your .env in place):
#   sh scripts/upgrade-postgres-18.sh
set -eu

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi
DB_NAME="${DB_NAME:-hibiscus}"
DB_USERNAME="${DB_USERNAME:-hibiscus}"

# Compose derives the project name from the directory unless overridden.
PROJECT="${COMPOSE_PROJECT_NAME:-$(basename "$PWD" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')}"
OLD_VOLUME="${PROJECT}_postgres-data"
HELPER="${PROJECT}-pg17-migrate"
DUMP="postgres17-${DB_NAME}-$(date +%Y%m%d-%H%M%S).dump"

if ! docker volume inspect "$OLD_VOLUME" >/dev/null 2>&1; then
  echo "No PostgreSQL 17 volume '$OLD_VOLUME' found - nothing to migrate."
  echo "(Set COMPOSE_PROJECT_NAME if you start the stack with a custom project name.)"
  exit 0
fi

wait_ready() {
  i=0
  until docker exec "$1" pg_isready -U "$DB_USERNAME" -d "$DB_NAME" >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -gt 60 ]; then
      echo "PostgreSQL in '$1' did not become ready" >&2
      exit 1
    fi
    sleep 1
  done
}

echo "==> Stopping Hibiscus and the database"
docker compose stop hibiscus postgres >/dev/null 2>&1 || true

echo "==> Dumping '$DB_NAME' from the PostgreSQL 17 volume '$OLD_VOLUME'"
docker rm -f "$HELPER" >/dev/null 2>&1 || true
# The volume already holds a cluster, so the entrypoint skips initdb and the
# password below is never used; it only satisfies the image's start check.
docker run -d --name "$HELPER" \
  -v "$OLD_VOLUME":/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=unused-existing-cluster \
  postgres:17-alpine >/dev/null
trap 'docker rm -f "$HELPER" >/dev/null 2>&1 || true' EXIT
wait_ready "$HELPER"
docker exec "$HELPER" pg_dump -U "$DB_USERNAME" -d "$DB_NAME" -Fc > "$DUMP"
OLD_TABLES=$(docker exec "$HELPER" psql -U "$DB_USERNAME" -d "$DB_NAME" -tAc \
  "select count(*) from information_schema.tables where table_schema='public'")
docker rm -f "$HELPER" >/dev/null
trap - EXIT
echo "    $OLD_TABLES tables, dump written to $DUMP"

echo "==> Starting PostgreSQL 18"
docker compose up -d postgres
wait_ready hibiscus-db

echo "==> Restoring into PostgreSQL 18"
docker exec -i hibiscus-db pg_restore -U "$DB_USERNAME" -d "$DB_NAME" \
  --clean --if-exists --no-owner --role="$DB_USERNAME" < "$DUMP"
NEW_TABLES=$(docker exec hibiscus-db psql -U "$DB_USERNAME" -d "$DB_NAME" -tAc \
  "select count(*) from information_schema.tables where table_schema='public'")
if [ "$NEW_TABLES" != "$OLD_TABLES" ]; then
  echo "Table count differs after restore: $OLD_TABLES before, $NEW_TABLES after." >&2
  echo "Hibiscus was NOT started. The old volume and $DUMP are untouched." >&2
  exit 1
fi
echo "    $NEW_TABLES tables restored"

echo "==> Starting Hibiscus"
docker compose up -d

echo
echo "Done. Keep $DUMP and the volume '$OLD_VOLUME' until you have checked Hibiscus,"
echo "then remove them:  docker volume rm $OLD_VOLUME && rm $DUMP"
