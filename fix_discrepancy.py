#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_crm.settings')
django.setup()

# Import models
from hospital.models import Doctor
from users.models import User, DoctorProfile
from django.db import transaction

@transaction.atomic
def fix_doctor_records():
    """Fix discrepancies between DoctorProfile and Doctor records"""
    
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
                    print(f"Fixed discrepancies for {user.username}:")
                    for d in discrepancies:
                        print(f"  - {d}")
                else:
                    print(f"No discrepancies for {user.username}")
                    
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
                print(f"Created missing Doctor record for {user.username}")
                
        except DoctorProfile.DoesNotExist:
            print(f"No DoctorProfile found for {user.username}")
    
    print(f"\nFixed records for {fixed_count} doctors")

if __name__ == "__main__":
    fix_doctor_records() 