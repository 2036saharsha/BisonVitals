from django.core.management.base import BaseCommand
from hospital.models import Doctor


class Command(BaseCommand):
    help = 'Checks doctor data in the database'

    def handle(self, *args, **options):
        self.stdout.write('Checking doctor data...')
        
        # Get all doctors
        doctors = Doctor.objects.all()
        self.stdout.write(f'Total doctors: {doctors.count()}')
        
        # Print each doctor's info
        for doctor in doctors:
            self.stdout.write(f'Doctor: {doctor.user.get_full_name()}')
            self.stdout.write(f'  Username: {doctor.user.username}')
            self.stdout.write(f'  Specialization: {doctor.specialization}')
            self.stdout.write(f'  Years of Experience: {doctor.years_of_experience}')
            self.stdout.write(f'  License: {doctor.license_number}')
            self.stdout.write('---')
        
        self.stdout.write(self.style.SUCCESS('Doctor data check complete!')) 