#!/bin/sh
set -e

echo "Starting Vocabbee backend..."
echo "Port: ${PORT:-8000}"
echo "Project root: /project"

cd /project

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --threads 4 \
  --timeout 120 \
  --access-logfile '-' \
  --error-logfile '-'