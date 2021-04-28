#!/usr/bin/env bash
# This is used to avoid having the "*" sign to get commands on bin
set -f 

if [ ! -d /var/log/postgres_backup/ ]; then
    mkdir -p /var/log/postgres_backup/
fi

export > /.env 

if [[ ${USE_S3} -eq "$TRUE" ]]; then
	apt-get install -y python3-pip --quiet=2 > /dev/null
	python3 -m pip install --upgrade --quiet pip

	echo "Installing virtualenv for PostgreSQL backup on S3..."
	python3 -m pip install --upgrade --quiet virtualenv
	counter=1
	max_retries=3
	# Under certain circumstances a race condition occurs. Virtualenv creation
	# fails because python cannot find `wheel` package folder
	# e.g. `FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/virtualenv/wheel/3.5/embed/1/wheel.json'`
	until $(virtualenv --quiet -p /usr/bin/python3 /tmp/backup-virtualenv > /dev/null)
	do
		[[ "$counter" -eq "$max_retries" ]] && echo "Virtual environment creation failed!" && exit 1
		((counter++))
	done
	. /tmp/backup-virtualenv/bin/activate
	pip install --quiet humanize smart-open==1.7.1
	pip install --quiet boto
	deactivate

	CRON_CMD="${POSTGRES_BACKUP_SCHEDULE} BASH_ENV=/.env bash /tmp/backup-virtualenv/bin/python /postgres-scripts/backup-to-s3.py > /srv/logs/backup.log 2>&1"
else
	CRON_CMD="${POSTGRES_BACKUP_SCHEDULE} BASH_ENV=/.env bash bash /kobo-docker-scripts/backup-to-disk.sh > /srv/logs/backup.log 2>&1"
fi

echo $CRON_CMD > /etc/crontabs/root

# Starting crond
crond &
# To reload crond  kb: https://dev.to/milolav/reload-cron-jobs-in-an-alpine-linux-container-486b
#touch /etc/crontabs/cron.update

## Initiating crond to manage cron job execution

echo "Crontab job to perform postgres backups set at: /etc/crontabs/root"