#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply migrations
python manage.py migrate

# (Optional) Run your custom management command
# Only include this line if you have fix_school_ids.py inside docrequest/management/commands/
python manage.py fix_school_ids || echo "No fix_school_ids command found, skipping."
