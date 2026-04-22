#!/usr/bin/env bash
# Render build script for SRAS
set -o errexit

echo "==> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running migrations..."
python manage.py migrate

echo "==> Creating admin user (if not exists)..."
python manage.py create_admin
