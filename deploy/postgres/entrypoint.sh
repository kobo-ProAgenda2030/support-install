#!/usr/bin/env bash
set -e
export POSTGRES_BACKUPS_DIR=/srv/backups
export POSTGRES_LOGS_DIR=/srv/logs

echo "Copying init scripts ..."

if [[ ! -d $POSTGRES_LOGS_DIR ]]; then
    mkdir -p $POSTGRES_LOGS_DIR
fi

if [[ ! -d $POSTGRES_BACKUPS_DIR ]]; then
    mkdir -p $POSTGRES_BACKUPS_DIR
fi

# Restore permissions
chmod +x -R ./postgres-scripts/

# Send backup installation process in background to avoid blocking PostgreSQL startup

echo "Registering Cron expression"
# Send backup installation process in background to avoid blocking PostgreSQL startup
bash ./postgres-scripts/register-cron.sh

exec sleep infinity
