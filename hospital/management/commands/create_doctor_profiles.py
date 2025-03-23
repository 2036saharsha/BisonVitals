from django.core.management.base import BaseCommand
from hospital.models import Doctor
from users.models import User, DoctorProfile
from django.db import transaction


class Command(BaseCommand):
    help = 'Create missing DoctorProfile records for doctors'

    @transaction.atomic
    def handle(self, *args, **options):
        """
        Find all doctors without a corresponding DoctorProfile and create one
        """
        self.stdout.write(self.style.NOTICE('Checking for doctors without DoctorProfiles...'))
        
        # Get all doctors
        doctors = Doctor.objects.all()
        
        created_count = 0
        for doctor in doctors:
            try:
                # Check if DoctorProfile exists
                DoctorProfile.objects.get(user=doctor.user)
                self.stdout.write(self.style.SUCCESS(f"DoctorProfile exists for {doctor.user.username}"))
                
            except DoctorProfile.DoesNotExist:
                # Create missing DoctorProfile
                DoctorProfile.objects.create(
                    user=doctor.user,
                    specialization=doctor.specialization,
                    license_number=doctor.license_number,
                    years_of_experience=doctor.years_of_experience,
                    bio=doctor.bio if doctor.bio else ""
                )
                created_count += 1
                self.stdout.write(self.style.WARNING(f"Created missing DoctorProfile for {doctor.user.username}"))
        
        self.stdout.write(self.style.SUCCESS(f"\nCreated {created_count} missing DoctorProfiles")) 