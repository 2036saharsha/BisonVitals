from django.core.management.base import BaseCommand
from hospital.models import Doctor
from users.models import User, DoctorProfile
from django.db import transaction


class Command(BaseCommand):
    help = 'Fix discrepancies between DoctorProfile and Doctor records'

    @transaction.atomic
    def handle(self, *args, **options):
        """
        Fix any discrepancies between DoctorProfile and Doctor records
        to ensure data consistency
        """
        self.stdout.write(self.style.NOTICE('Checking doctor records for discrepancies...'))
        
        # Get all doctor users
        doctor_users = User.objects.filter(user_type='doctor')
        
        fixed_count = 0
        for user in doctor_users:
            try:
                # Get doctor profile
                profile = DoctorProfile.objects.get(user=user)
                
                # Get doctor record
                try:
                    doctor = Doctor.objects.get(user=user)
                    
                    # Check for discrepancies
                    discrepancies = []
                    if doctor.specialization != profile.specialization:
                        discrepancies.append(f"Specialization: '{doctor.specialization}' vs '{profile.specialization}'")
                        doctor.specialization = profile.specialization
                    
                    if doctor.license_number != profile.license_number:
                        discrepancies.append(f"License: '{doctor.license_number}' vs '{profile.license_number}'")
                        doctor.license_number = profile.license_number
                        
                    if doctor.years_of_experience != profile.years_of_experience:
                        discrepancies.append(f"Experience: {doctor.years_of_experience} vs {profile.years_of_experience}")
                        doctor.years_of_experience = profile.years_of_experience
                        
                    if doctor.bio != profile.bio:
                        discrepancies.append("Bio text differs")
                        doctor.bio = profile.bio
                    
                    # If any discrepancies found
                    if discrepancies:
                        doctor.save()
                        fixed_count += 1
                        self.stdout.write(self.style.WARNING(f"Fixed discrepancies for {user.username}:"))
                        for d in discrepancies:
                            self.stdout.write(f"  - {d}")
                    else:
                        self.stdout.write(self.style.SUCCESS(f"No discrepancies for {user.username}"))
                        
                except Doctor.DoesNotExist:
                    # Create doctor record if it doesn't exist
                    doctor = Doctor.objects.create(
                        user=user,
                        specialization=profile.specialization,
                        license_number=profile.license_number,
                        years_of_experience=profile.years_of_experience,
                        bio=profile.bio
                    )
                    fixed_count += 1
                    self.stdout.write(self.style.WARNING(f"Created missing Doctor record for {user.username}"))
                    
            except DoctorProfile.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"No DoctorProfile found for {user.username}"))
        
        self.stdout.write(self.style.SUCCESS(f"\nFixed records for {fixed_count} doctors")) 