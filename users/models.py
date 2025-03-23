from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    )
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    
    def is_doctor(self):
        return self.user_type == 'doctor'
    
    def is_patient(self):
        return self.user_type == 'patient'


class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"


class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    blood_group = models.CharField(max_length=5, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_number = models.CharField(max_length=17, blank=True)
    allergies = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)
    
    def __str__(self):
        return f"Patient: {self.user.get_full_name()}"

# Signal handlers to keep Doctor and DoctorProfile in sync
@receiver(post_save, sender=DoctorProfile)
def update_doctor_from_profile(sender, instance, **kwargs):
    """
    Signal handler to update Doctor record when DoctorProfile is saved
    """
    from hospital.models import Doctor
    
    try:
        # Try to update existing Doctor record
        doctor = Doctor.objects.get(user=instance.user)
        
        # Update only if fields have changed
        if (doctor.specialization != instance.specialization or
            doctor.license_number != instance.license_number or
            doctor.years_of_experience != instance.years_of_experience or
            doctor.bio != instance.bio):
            
            # Update fields from DoctorProfile
            doctor.specialization = instance.specialization
            doctor.license_number = instance.license_number
            doctor.years_of_experience = instance.years_of_experience
            doctor.bio = instance.bio
            doctor.save()
    except Doctor.DoesNotExist:
        # Doctor record doesn't exist yet - let the form create it
        # We won't create it here to avoid potential race conditions
        pass
