#!/usr/bin/env bash

python manage.py collectstatic --noinput
python manage.py migrate

python manage.py createsuperuser \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "$DJANGO_SUPERUSER_EMAIL" \
    --noinput