from django.urls import path
from django.views.generic.base import RedirectView
from . import views

app_name = 'hospital'  # Add namespace for hospital app URLs

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Patient-facing views
    path('issue/create/', views.create_issue, name='create_issue'),
    path('issue/<int:issue_id>/recommendations/', views.doctor_recommendations, name='doctor_recommendations'),
    
    # Legacy URL redirect - for compatibility with old links
    path('issue/<int:issue_id>/doctors/', RedirectView.as_view(pattern_name='hospital:doctor_recommendations'), name='old_doctor_recommendations'),
    
    path('doctors/browse/', views.browse_doctors, name='browse_doctors'),
    path('doctor/<int:doctor_id>/book/<int:issue_id>/', views.book_appointment, name='book_appointment'),
    path('doctor/<int:doctor_id>/book/', views.direct_book_appointment, name='direct_book_appointment'),
    path('appointments/patient/', views.patient_appointments, name='patient_appointments'),
    path('patient/medical-history/', views.patient_medical_history, name='patient_medical_history'),
    
    # Doctor-facing views
    path('appointments/doctor/', views.doctor_appointments, name='doctor_appointments'),
    path('patient/<int:patient_id>/medical-history/', views.patient_medical_history, name='patient_medical_history_by_doctor'),
    
    # Shared views
    path('appointment/<int:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    
    # Add this new URL pattern for doctor_patients
    path('doctor/patients/', views.doctor_patients, name='doctor_patients'),
    
    # Vital signs visualization
    path('vital-signs/', views.vital_signs_dashboard, name='vital_signs_dashboard'),
    path('vital-signs/<int:issue_id>/', views.vital_signs_dashboard, name='vital_signs_dashboard_for_issue'),
] 