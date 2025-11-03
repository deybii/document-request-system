#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Fix school IDs (optional, skip if fails)
python manage.py fix_school_ids || echo "Skipped fix_school_ids"