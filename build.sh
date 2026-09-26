#!/usr/bin/env bash

python manage.py collectstatic --noinput
python manage.py migrate

# TEMPORARY: create admin account
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput || true
fi