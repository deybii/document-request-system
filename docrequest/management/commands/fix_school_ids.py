from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from docrequest.models import UserProfile

class Command(BaseCommand):
    help = 'Fix missing or empty school_ids for existing user profiles'

    def handle(self, *args, **kwargs):
        fixed_count = 0
        created_count = 0
        already_valid = 0
        
        self.stdout.write(self.style.WARNING('='*60))
        self.stdout.write(self.style.WARNING('Starting School ID Fix Process...'))
        self.stdout.write(self.style.WARNING('='*60 + '\n'))
        
        # Process all users
        all_users = User.objects.all()
        total_users = all_users.count()
        
        self.stdout.write(f'Found {total_users} user(s) to process...\n')
        
        for user in all_users:
            # Skip superuser if no profile needed
            if user.is_superuser and not hasattr(user, 'profile'):
                self.stdout.write(
                    self.style.WARNING(f'⊗ Skipping superuser: {user.username}')
                )
                continue
            
            # Check if user has a profile
            if not hasattr(user, 'profile'):
                # Create profile
                if user.username.isdigit() and len(user.username) == 8:
                    school_id = user.username
                else:
                    # Generate school_id: current year + user ID (padded to 4 digits)
                    school_id = f"{2025}{user.id:04d}"
                
                profile = UserProfile.objects.create(
                    user=user,
                    school_id=school_id,
                    role='student',
                    is_verified=user.is_staff or user.is_superuser
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Created profile for: {user.username:15} (ID: {user.id:3}) → School ID: {school_id}'
                    )
                )
            else:
                profile = user.profile
                
                # Check if school_id is empty or None
                if not profile.school_id or profile.school_id.strip() == '':
                    # Try to use username if it's valid
                    if user.username.isdigit() and len(user.username) == 8:
                        profile.school_id = user.username
                    else:
                        # Generate school_id
                        profile.school_id = f"{2025}{user.id:04d}"
                    
                    profile.save()
                    fixed_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠️  Fixed empty ID for: {user.username:15} (ID: {user.id:3}) → School ID: {profile.school_id}'
                        )
                    )
                else:
                    already_valid += 1
                    self.stdout.write(
                        f'   Valid profile for: {user.username:15} (ID: {user.id:3}) → School ID: {profile.school_id}'
                    )
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 SUMMARY REPORT:'))
        self.stdout.write('='*60)
        self.stdout.write(f'  • Total users processed:    {total_users}')
        self.stdout.write(f'  • New profiles created:     {created_count}')
        self.stdout.write(f'  • Empty IDs fixed:          {fixed_count}')
        self.stdout.write(f'  • Already valid:            {already_valid}')
        self.stdout.write('='*60 + '\n')
        
        if created_count > 0 or fixed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ SUCCESS! Fixed {created_count + fixed_count} user profile(s)!\n'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ All user profiles already have valid school IDs!\n')
            )
        
        # Show next steps
        self.stdout.write(self.style.WARNING('📋 Next Steps:'))
        self.stdout.write('  1. Visit /admin/docrequest/userprofile/ to verify')
        self.stdout.write('  2. Log in as a user to test the navigation dropdown')
        self.stdout.write('  3. Check that School ID appears in user profile\n')