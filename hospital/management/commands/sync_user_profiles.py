from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import User
from hospital.models import Doctor, Patient


class Command(BaseCommand):
    help = 'Synchronizes User objects with their corresponding Doctor/Patient records'

    def handle(self, *args, **options):
        self.stdout.write('Starting user profile synchronization...')
        
        # Process doctors
        doctor_users = User.objects.filter(user_type='doctor')
        self.stdout.write(f'Found {doctor_users.count()} doctor users')
        
        with transaction.atomic():
            for user in doctor_users:
                if not hasattr(user, 'doctor'):
                    doctor = Doctor.objects.create(
                        user=user,
                        specialization='General Medicine',
                        license_number=f'TMP-{user.id}',
                        years_of_experience=0
                    )
                    self.stdout.write(f'Created Doctor record for {user.username}')
        
        # Process patients
        patient_users = User.objects.filter(user_type='patient')
        self.stdout.write(f'Found {patient_users.count()} patient users')
        
        with transaction.atomic():
            for user in patient_users:
                if not hasattr(user, 'patient'):
                    patient = Patient.objects.create(
                        user=user
                    )
                    self.stdout.write(f'Created Patient record for {user.username}')
        
        self.stdout.write(self.style.SUCCESS('User profile synchronization complete!')) 