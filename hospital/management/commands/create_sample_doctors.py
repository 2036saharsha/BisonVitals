from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from users.models import User
from hospital.models import Doctor


class Command(BaseCommand):
    help = 'Creates sample doctors with different specializations'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample doctors...')
        
        specializations = [
            'General Medicine',
            'Cardiology',
            'Neurology',
            'Orthopedics',
            'Dermatology',
            'Pediatrics',
            'ENT',
            'Psychiatry',
            'Ophthalmology',
            'Gastroenterology'
        ]
        
        with transaction.atomic():
            created_count = 0
            
            for i, specialization in enumerate(specializations, 1):
                username = f'doctor{i}'
                
                # Check if user exists
                try:
                    user = User.objects.get(username=username)
                    self.stdout.write(f'User {username} already exists, updating to doctor type')
                    user.user_type = 'doctor'
                    user.save()
                except User.DoesNotExist:
                    # Create user
                    user = User.objects.create(
                        username=username,
                        first_name=f'Doctor{i}',
                        last_name='Smith',
                        email=f'doctor{i}@example.com',
                        user_type='doctor'
                    )
                    
                    # Set a simple password
                    user.set_password('doctor123')
                    user.save()
                
                # Create or update doctor profile
                doctor, created = Doctor.objects.update_or_create(
                    user=user,
                    defaults={
                        'specialization': specialization,
                        'license_number': f'LIC-{slugify(specialization)}',
                        'years_of_experience': 5 + i,
                        'bio': f"Experienced {specialization} specialist with {5+i} years of practice. Specializes in treating various conditions related to {specialization.lower()}."
                    }
                )
                
                status = 'Created' if created else 'Updated'
                created_count += 1
                self.stdout.write(f'{status} {specialization} doctor: {user.get_full_name()}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} sample doctors')) 