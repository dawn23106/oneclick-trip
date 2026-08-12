#!/usr/bin/env bash
set -euo pipefail

project_dir="${ONECLICK_TRIP_DIR:-/opt/oneclick-trip}"
backup_dir="${ONECLICK_TRIP_BACKUP_DIR:-/opt/oneclick-trip/backups/mysql}"
retention_days="${ONECLICK_TRIP_BACKUP_RETENTION_DAYS:-7}"

cd "$project_dir"
umask 077
mkdir -p "$backup_dir"

timestamp="$(date +%Y%m%d-%H%M%S)"
temporary="$backup_dir/oneclick-trip-$timestamp.sql.gz.part"
destination="$backup_dir/oneclick-trip-$timestamp.sql.gz"

cleanup() {
  rm -f "$temporary"
}
trap cleanup EXIT

docker compose --env-file .env -f compose.production.yml exec -T mysql sh -c \
  'exec mysqldump --single-transaction --quick --no-tablespaces --routines --triggers -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' \
  | gzip -9 > "$temporary"

test -s "$temporary"
mv "$temporary" "$destination"
find "$backup_dir" -type f -name 'oneclick-trip-*.sql.gz' -mtime "+$retention_days" -delete
echo "MySQL backup created: $destination"
