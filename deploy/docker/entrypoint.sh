#!/bin/sh
set -e

echo "Starting Vocabbee backend..."

cd /project

echo "Running migrations..."
python manage.py migrate --noinput

# Export container environment for cron
printenv > /etc/environment

echo "Installing cron jobs..."
python manage.py crontab remove || true
python manage.py crontab add

echo "Starting cron..."
service cron start

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --threads 4 \
  --timeout 120 \
  --access-logfile '-' \
  --error-logfile '-'