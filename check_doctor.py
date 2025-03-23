#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_crm.settings')
django.setup()

# Import models
from hospital.models import Doctor
from users.models import User, DoctorProfile

# Check user profile
try:
    user = User.objects.get(username='Sameer')
    print(f"User: {user.username}")
    print(f"User Type: {user.user_type}")
    
    # Check doctor profile
    try:
        profile = DoctorProfile.objects.get(user=user)
        print(f"DoctorProfile Found - Specialization: {profile.specialization}")
    except DoctorProfile.DoesNotExist:
        print("No DoctorProfile found")
        
    # Check doctor record
    try:
        doctor = Doctor.objects.get(user=user)
        print(f"Doctor Record Found - Specialization: {doctor.specialization}")
    except Doctor.DoesNotExist:
        print("No Doctor record found")
        
except User.DoesNotExist:
    print("User 'Sameer' not found") 