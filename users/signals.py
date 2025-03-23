from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import DoctorProfile
from hospital.models import Doctor

@receiver(post_save, sender=DoctorProfile)
def update_doctor_from_profile(sender, instance, **kwargs):
    """
    Signal handler to update Doctor record when DoctorProfile is saved
    """
    try:
        # Try to update existing Doctor record
        doctor = Doctor.objects.get(user=instance.user)
        
        # Update only if fields have changed
        if (doctor.specialization != instance.specialization or
            doctor.license_number != instance.license_number or
            doctor.years_of_experience != instance.years_of_experience or
            doctor.bio != instance.bio):
            
            print(f"Syncing Doctor record with DoctorProfile for {instance.user.username}")
            
            # Update fields from DoctorProfile
            doctor.specialization = instance.specialization
            doctor.license_number = instance.license_number
            doctor.years_of_experience = instance.years_of_experience
            doctor.bio = instance.bio
            
            # Disable the signal temporarily to avoid infinite recursion
            post_save.disconnect(update_doctor_from_profile, sender=DoctorProfile)
            doctor.save()
            post_save.connect(update_doctor_from_profile, sender=DoctorProfile)
            
    except Doctor.DoesNotExist:
        # Doctor record doesn't exist yet - let the form create it
        # We won't create it here to avoid potential race conditions
        pass

@receiver(post_save, sender=Doctor)
def update_profile_from_doctor(sender, instance, **kwargs):
    """
    Signal handler to update DoctorProfile record when Doctor is saved
    """
    try:
        # Try to update existing DoctorProfile
        profile = DoctorProfile.objects.get(user=instance.user)
        
        # Update only if fields have changed
        if (profile.specialization != instance.specialization or
            profile.license_number != instance.license_number or
            profile.years_of_experience != instance.years_of_experience or
            profile.bio != instance.bio):
            
            print(f"Syncing DoctorProfile with Doctor record for {instance.user.username}")
            
            # Update fields from Doctor
            profile.specialization = instance.specialization
            profile.license_number = instance.license_number
            profile.years_of_experience = instance.years_of_experience
            profile.bio = instance.bio
            
            # Disable the signal temporarily to avoid infinite recursion
            post_save.disconnect(update_profile_from_doctor, sender=Doctor)
            profile.save()
            post_save.connect(update_profile_from_doctor, sender=Doctor)
            
    except DoctorProfile.DoesNotExist:
        # Profile doesn't exist yet
        pass 