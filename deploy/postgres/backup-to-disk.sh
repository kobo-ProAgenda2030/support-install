#!/bin/bash
set -e

DBDATESTAMP="$(date +%Y.%m.%d.%H_%M)"
BACKUP_FILENAME="postgres-support-${DBDATESTAMP}.pg_dump"
cd /srv/backups
rm -rf *.pg_dump

PGPASSWORD=${SUPPORT_DB_PASSWORD} pg_dump -U ${SUPPORT_DB_USER} --port ${SUPPORT_DB_PORT} -h ${KOBO_DB_SERVER} -d ${SUPPORT_DB_NAME} --format=custom > "${BACKUP_FILENAME}"

echo "Backup files at ${BACKUP_FILENAME} created successfully."