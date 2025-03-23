from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import User

# Create your models here.
class Doctor(models.Model):
    """Doctor model representing a doctor in the system"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor')
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"

class Patient(models.Model):
    """Patient model representing a patient in the system"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient')
    date_of_birth = models.DateField(null=True, blank=True)
    blood_group = models.CharField(max_length=10, blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()}"

class DiseaseType(models.Model):
    """Disease type model representing different types of diseases"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    recommended_specialization = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_common_types(cls):
        """Returns a list of common disease types"""
        common_types = [
            'Fever',
            'Cold and Flu',
            'Headache',
            'Allergies',
            'Stomach Pain',
            'Back Pain',
            'Joint Pain',
            'Skin Rash',
            'Respiratory Issues',
            'Eye Problems',
            'Ear Infection',
            'Dental Issues',
            'Urinary Tract Infection',
            'High Blood Pressure',
            'Diabetes',
            'Anxiety',
            'Depression',
            'Insomnia',
            'Digestive Issues',
            'General Checkup'
        ]
        return common_types

class Issue(models.Model):
    """Issue model representing a health issue reported by a patient"""
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('emergency', 'Emergency'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='issues')
    disease_type = models.ForeignKey(DiseaseType, on_delete=models.SET_NULL, null=True, blank=True, related_name='issues')
    custom_disease_type = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    symptoms = models.TextField(blank=True, null=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')
    device_data = models.CharField(max_length=255, blank=True, null=True, help_text="Path to CSV file containing vital signs data")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        disease_name = self.disease_type.name if self.disease_type else self.custom_disease_type
        return f"{disease_name} - {self.patient}"

class Appointment(models.Model):
    """Appointment model representing a scheduled meeting between a doctor and a patient"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    notes = models.TextField(blank=True, null=True)
    doctor_notes = models.TextField(blank=True, null=True)
    patient_feedback = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Appointment with Dr. {self.doctor.user.last_name} for {self.patient.user.get_full_name()} on {self.appointment_date}"
    
    class Meta:
        ordering = ['appointment_date', 'appointment_time']

class Alert(models.Model):
    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('viewed', 'Viewed'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved')
    ]

    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='alerts')
    doctor = models.ForeignKey('Doctor', on_delete=models.CASCADE, related_name='alerts')
    issue = models.ForeignKey('Issue', on_delete=models.CASCADE, related_name='alerts')
    
    timestamp = models.DateTimeField(default=timezone.now)
    alert_time = models.DateTimeField()  # The time of the anomaly in the data
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='new')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    vital_signs_data = models.JSONField()  # Store the relevant vital signs that triggered the alert
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-alert_time', '-urgency']
        indexes = [
            models.Index(fields=['-alert_time']),
            models.Index(fields=['status']),
            models.Index(fields=['doctor', 'status']),
        ]

    def __str__(self):
        return f"Alert for {self.patient} - {self.title} ({self.get_urgency_display()})"

# Signal handlers to ensure Doctor and Patient records exist for respective users
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler to ensure Doctor and Patient records are created
    when a User object is saved with the corresponding user_type
    """
    # If user_type is not set, we can't determine what to create
    if not instance.user_type:
        return

    if instance.user_type == 'doctor':
        # Create Doctor record if it doesn't exist
        try:
            doctor = instance.doctor
        except (Doctor.DoesNotExist, AttributeError):
            doctor, doctor_created = Doctor.objects.get_or_create(
                user=instance,
                defaults={
                    'specialization': 'General Medicine',
                    'license_number': f'TMP-{instance.id}',
                    'years_of_experience': 0
                }
            )
            
            # Create DoctorProfile if it doesn't exist
            from users.models import DoctorProfile
            try:
                DoctorProfile.objects.get(user=instance)
            except DoctorProfile.DoesNotExist:
                # Create matching DoctorProfile with same data
                DoctorProfile.objects.create(
                    user=instance,
                    specialization=doctor.specialization,
                    license_number=doctor.license_number,
                    years_of_experience=doctor.years_of_experience,
                    bio=doctor.bio if doctor.bio else ""
                )
    
    elif instance.user_type == 'patient':
        # Create Patient if it doesn't exist
        try:
            patient = instance.patient
        except (Patient.DoesNotExist, AttributeError):
            patient, patient_created = Patient.objects.get_or_create(
                user=instance
            )
