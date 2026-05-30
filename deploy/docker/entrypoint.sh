#!/bin/sh

set -e

echo “Starting Vocabbee backend…”
echo “Port: ${PORT:-8000}”
echo “Project root: $(pwd)”

Wait for PostgreSQL

echo “Waiting for PostgreSQL…”

until python manage.py check –database default >/dev/null 2>&1
do
echo “Database unavailable - sleeping”
sleep 2
done

echo “Database available”

Run migrations

python manage.py migrate –noinput

Collect static files (optional)

python manage.py collectstatic –noinput || true

Start Gunicorn

exec gunicorn config.wsgi:application
–bind 0.0.0.0:8000
–workers 2
–threads 4
–timeout 120