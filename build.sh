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

# Fix school IDs
python manage.py fix_school_ids || echo "Skipped fix_school_ids"

# ✅ Create admin user
echo "Creating admin user..."
python manage.py shell << 'EOF'
import os
from django.contrib.auth.models import User
from docrequest.models import UserProfile

school_id = os.getenv('ADMIN_SCHOOL_ID', '20250001')
email = os.getenv('ADMIN_EMAIL', 'admin@cityofmalabonuniversity.edu.ph')
password = os.getenv('ADMIN_PASSWORD', 'Admin@2025')

print(f"Attempting to create admin with School ID: {school_id}")

if not User.objects.filter(username=school_id).exists():
    try:
        user = User.objects.create_superuser(
            username=school_id,
            email=email,
            password=password,
            first_name='System',
            last_name='Administrator'
        )
        
        UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'school_id': school_id,
                'role': 'student',
                'is_verified': True
            }
        )
        
        print('✅ Admin user created successfully!')
        print(f'   School ID: {school_id}')
        print(f'   Email: {email}')
        print(f'   Access admin at: /admin/')
        print(f'   Access dashboard at: /admin-dashboard/')
    except Exception as e:
        print(f'❌ Error creating admin: {e}')
else:
    print(f'✅ Admin user already exists: {school_id}')
EOF

echo "Build completed!"