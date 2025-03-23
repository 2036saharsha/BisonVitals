from django.contrib import admin
from .models import DiseaseType, Issue, Appointment, Doctor, Patient

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'license_number', 'years_of_experience')
    list_filter = ('specialization', 'years_of_experience')
    search_fields = ('user__first_name', 'user__last_name', 'license_number', 'specialization')

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_of_birth', 'blood_group')
    list_filter = ('blood_group',)
    search_fields = ('user__first_name', 'user__last_name', 'allergies')

@admin.register(DiseaseType)
class DiseaseTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'recommended_specialization')
    list_filter = ('recommended_specialization',)
    search_fields = ('name', 'description', 'recommended_specialization')

@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('get_patient_name', 'get_disease_name', 'severity', 'status', 'created_at')
    list_filter = ('severity', 'status', 'created_at')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'disease_type__name', 'custom_disease_type', 'description', 'symptoms')
    date_hierarchy = 'created_at'
    
    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()
    get_patient_name.short_description = 'Patient'
    
    def get_disease_name(self, obj):
        return obj.disease_type.name if obj.disease_type else obj.custom_disease_type
    get_disease_name.short_description = 'Disease'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('get_patient_name', 'get_doctor_name', 'appointment_date', 'appointment_time', 'status')
    list_filter = ('appointment_date', 'status', 'doctor__specialization')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'doctor__user__first_name', 'doctor__user__last_name')
    date_hierarchy = 'appointment_date'
    
    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()
    get_patient_name.short_description = 'Patient'
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"
    get_doctor_name.short_description = 'Doctor'
