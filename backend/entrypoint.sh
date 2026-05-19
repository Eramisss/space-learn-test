#!/bin/sh
set -e

echo "==> Ожидаю PostgreSQL на $DB_HOST:$DB_PORT..."
until python -c "import socket; socket.create_connection(('$DB_HOST', int('$DB_PORT')), timeout=2)" 2>/dev/null; do
    sleep 1
done
echo "==> PostgreSQL доступен"

echo "==> Применяю миграции"
python manage.py makemigrations accounts decks cards reviews --noinput
python manage.py migrate --noinput

echo "==> Собираю статику"
python manage.py collectstatic --noinput

echo "==> Запускаю $@"
exec "$@"
