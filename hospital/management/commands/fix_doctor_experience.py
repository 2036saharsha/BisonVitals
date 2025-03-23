from django.core.management.base import BaseCommand
from django.db import transaction
from hospital.models import Doctor
from users.models import DoctorProfile


class Command(BaseCommand):
    help = 'Fixes doctor experience data by syncing with DoctorProfile'

    def handle(self, *args, **options):
        self.stdout.write('Fixing doctor experience data...')
        
        doctor_username = options.get('username')
        fixed_count = 0
        
        with transaction.atomic():
            # Get all doctors
            if doctor_username:
                doctors = Doctor.objects.filter(user__username=doctor_username)
                self.stdout.write(f'Checking doctor: {doctor_username}')
            else:
                doctors = Doctor.objects.all()
                self.stdout.write(f'Checking all doctors: {doctors.count()}')
            
            # Check each doctor
            for doctor in doctors:
                try:
                    # Try to find matching doctor profile
                    doctor_profile = DoctorProfile.objects.get(user=doctor.user)
                    
                    # Check if there's a mismatch
                    if doctor.years_of_experience != doctor_profile.years_of_experience:
                        self.stdout.write(f'Updating {doctor.user.username}: {doctor.years_of_experience} -> {doctor_profile.years_of_experience} years')
                        
                        # Update from DoctorProfile to Doctor
                        doctor.years_of_experience = doctor_profile.years_of_experience
                        doctor.save()
                        fixed_count += 1
                    else:
                        self.stdout.write(f'No mismatch for {doctor.user.username}: {doctor.years_of_experience} years')
                
                except DoctorProfile.DoesNotExist:
                    self.stdout.write(f'No DoctorProfile found for {doctor.user.username}')
        
        self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} doctor records'))
    
    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username of a specific doctor to fix') 