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

echo "==> Seeding grade scale..."
python manage.py seed_engine

echo "==> Creating admin user (if not exists)..."
python manage.py create_admin

echo "==> Seeding default teacher & student..."
python manage.py seed_data

echo "==> Build complete!"
