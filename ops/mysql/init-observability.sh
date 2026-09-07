#!/bin/sh
set -eu

# The application only needs the normalized digest table. It cannot read raw
# statements, credentials, process lists or other performance_schema tables.
mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL
GRANT SELECT ON performance_schema.events_statements_summary_by_digest
  TO '${MYSQL_USER}'@'%';
FLUSH PRIVILEGES;
EOSQL
