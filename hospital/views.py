from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect, JsonResponse, Http404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import Issue, Appointment, DiseaseType, Doctor, Patient, Issue, Alert
from .forms import IssueForm, AppointmentForm, DoctorFilterForm
from users.models import User, DoctorProfile, PatientProfile
from .visualization import generate_vital_signs_plots

import json
import requests
import os
from django.conf import settings
from dotenv import load_dotenv
import subprocess
import threading
import webbrowser
import time
import pickle

# Helper functions
def get_patient_profile(user):
    """Get the patient profile for the current user"""
    if not user.is_authenticated or not user.is_patient():
        return None
    return PatientProfile.objects.get(user=user)

def get_doctor_profile(user):
    """Get the doctor profile for the current user"""
    if not user.is_authenticated or not user.is_doctor():
        return None
    return DoctorProfile.objects.get(user=user)

def generate_medical_summary(patient_issues):
    """Generate a medical summary for a patient using Gemini API"""
    if not patient_issues:
        return "No previous medical history found."
    
    try:
        # Import the Gemini API library
        import google.generativeai as genai
        import json
        import os
        from dotenv import load_dotenv
        
        # Load environment variables from .env file
        load_dotenv()
        
        # Format patient issues for the prompt
        issue_texts = []
        for issue in patient_issues:
            disease = issue.disease_type.name if issue.disease_type else issue.custom_disease_type
            symptoms = issue.symptoms if issue.symptoms else "No symptoms reported"
            description = issue.description if issue.description else "No description provided"
            date = issue.created_at.strftime('%Y-%m-%d')
            severity = issue.get_severity_display()
            status = issue.get_status_display()
            
            issue_text = f"""
            Issue: {disease}
            Date: {date}
            Severity: {severity}
            Status: {status}
            Symptoms: {symptoms}
            Description: {description}
            """
            issue_texts.append(issue_text)
        
        # Get API key from .env file using dotenv
        api_key = os.getenv('GEMINI_API_KEY')
        
        # If no API key, fall back to default summary
        if not api_key:
            print("No Gemini API key found in .env file. Falling back to default summary.")
            return default_medical_summary(patient_issues)
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Select the model
        model = genai.GenerativeModel('gemini-2.0-pro-exp-02-05')
        
        # Build the prompt for Gemini
        prompt = f"""
        You are a medical assistant tasked with summarizing a patient's medical history. 
        Below are the patient's medical issues in chronological order. 
        Please provide a concise, professional summary of their medical history that would be useful for a doctor.
        
        Patient Medical Issues:
        
        {" ".join(issue_texts)}
        
        Create a comprehensive yet concise summary (maximum 200 words) that:
        1. Highlights key medical conditions and their progression
        2. Notes any patterns or recurring issues
        3. Identifies significant symptoms that might require attention
        4. Makes connections between related issues where appropriate
        
        Format your response as a professional medical summary without any preamble or meta-text.
        """
        
        # Generate the response
        response = model.generate_content(prompt)
        
        # Return the summary
        return response.text.strip()
        
    except Exception as e:
        print(f"Error generating medical summary with Gemini API: {e}")
        # Fall back to default summary
        return default_medical_summary(patient_issues)

def default_medical_summary(patient_issues):
    """Generate a default medical summary when API is unavailable"""
    if not patient_issues:
        return "No previous medical history found."
    
    # Create a basic summary of recent issues
    recent_issues = [i.disease_type.name if i.disease_type else i.custom_disease_type for i in patient_issues[:3]]
    recent_issues_str = ", ".join(recent_issues) if recent_issues else "no specific conditions"
    
    return f"Patient has a history of {len(patient_issues)} medical issues. Most recent issues include {recent_issues_str}. Detailed medical records are available in the history section below."


# Issue Views
@login_required
def dashboard(request):
    """Dashboard view for different user types"""
    # Initialize default context with empty values
    context = {
        'upcoming_appointments': [],
        'upcoming_appointments_count': 0,
        'today_appointments': [],
        'today_appointments_count': 0,
        'recent_issues': [],
    }
    
    # Get upcoming appointments count
    if request.user.is_doctor():
        # For doctor
        try:
            doctor = Doctor.objects.get(user=request.user)
            # Add this line to get new alerts count
            new_alerts_count = Alert.objects.filter(doctor=doctor, status='new').count()
            
            appointments_queryset = Appointment.objects.filter(
                doctor=doctor,
                appointment_date__gte=timezone.now().date(),
                status='scheduled'
            ).order_by('appointment_date', 'appointment_time')
            
            # Force evaluation by converting to list
            upcoming_appointments = list(appointments_queryset)
            
            # Get today's appointments
            today = timezone.now().date()
            today_appointments = [a for a in upcoming_appointments if a.appointment_date == today]
            
            # Get statistics
            total_patients = Patient.objects.filter(
                appointments__doctor=doctor
            ).distinct().count()
            
            weekly_appointments_count = Appointment.objects.filter(
                doctor=doctor,
                appointment_date__gte=today,
                appointment_date__lt=today + timedelta(days=7)
            ).count()
            
            monthly_appointments_count = Appointment.objects.filter(
                doctor=doctor,
                appointment_date__gte=today,
                appointment_date__lt=today + timedelta(days=30)
            ).count()
            
            completed_appointments_count = Appointment.objects.filter(
                doctor=doctor,
                status='completed'
            ).count()
            
            # Get recent patients
            recent_patients = Patient.objects.filter(
                appointments__doctor=doctor
            ).distinct().order_by('-appointments__appointment_date')[:5]
            
            context.update({
                'upcoming_appointments': upcoming_appointments[:5] if len(upcoming_appointments) > 5 else upcoming_appointments,
                'today_appointments': today_appointments,
                'upcoming_appointments_count': len(upcoming_appointments),
                'today_appointments_count': len(today_appointments),
                'total_patients': total_patients,
                'weekly_appointments_count': weekly_appointments_count,
                'monthly_appointments_count': monthly_appointments_count,
                'completed_appointments_count': completed_appointments_count,
                'recent_patients': recent_patients,
                'new_alerts_count': new_alerts_count,
            })
        except Exception as e:
            print(f"Error in doctor dashboard: {e}")
            messages.error(request, "Your doctor profile is not set up correctly. Please contact support.")
            
    elif request.user.is_patient():
        # For patient
        try:
            # Use get_or_create instead of just get to ensure the Patient record exists
            patient, created = Patient.objects.get_or_create(user=request.user)
            
            # Query for upcoming appointments
            appointments_queryset = Appointment.objects.filter(
                patient=patient,
                appointment_date__gte=timezone.now().date(),
                status='scheduled'
            ).order_by('appointment_date', 'appointment_time')
            
            # Force evaluation by converting to list
            upcoming_appointments = list(appointments_queryset)
            
            # Print debug information
            print(f"Patient {patient.id}: Found {len(upcoming_appointments)} upcoming appointments")
            for appt in upcoming_appointments:
                print(f"Appointment #{appt.id}: {appt.appointment_date} at {appt.appointment_time}")
            
            # Get recent issues
            recent_issues = Issue.objects.filter(
                patient=patient
            ).order_by('-created_at')[:5]
            
            # Get doctor specializations
            doctor_specializations = Doctor.objects.values_list('specialization', flat=True).distinct()
            
            context.update({
                'upcoming_appointments': upcoming_appointments[:5] if len(upcoming_appointments) > 5 else upcoming_appointments,
                'upcoming_appointments_count': len(upcoming_appointments),
                'recent_issues': recent_issues,
                'doctor_specializations': doctor_specializations,
            })
        except Exception as e:
            print(f"Error in patient dashboard: {e}")
            messages.error(request, f"Error retrieving your profile: {e}")
            
    elif request.user.is_staff:
        # For admin
        total_doctors = Doctor.objects.count()
        total_patients = Patient.objects.count()
        total_appointments = Appointment.objects.count()
        total_disease_types = DiseaseType.objects.count()
        
        # Recent activity placeholder - in a real app, you would implement an activity log
        recent_activity = []
        
        context.update({
            'total_doctors': total_doctors,
            'total_patients': total_patients,
            'total_appointments': total_appointments,
            'total_disease_types': total_disease_types,
            'recent_activity': recent_activity,
            'last_backup_date': timezone.now() - timedelta(days=1),  # Placeholder
        })
    
    if request.user.is_authenticated and request.user.is_doctor():
        try:
            doctor = Doctor.objects.get(user=request.user)
            context['has_new_alerts'] = Alert.objects.filter(doctor=doctor, status='new').exists()
        except Doctor.DoesNotExist:
            context['has_new_alerts'] = False
    
    return render(request, 'hospital/dashboard.html', context)

@login_required
def create_issue(request):
    """View for patients to report health issues"""
    # Check if user is a patient using the user_type field instead of relying on the related object
    if not request.user.is_patient():
        messages.error(request, "Only patients can report health issues.")
        return redirect('dashboard')
    
    # Ensure the patient object exists
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.error(request, "Your patient profile is not set up correctly. Please contact support.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = IssueForm(request.POST, request.FILES)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.patient = patient
            
            # Handle device data
            if form.cleaned_data.get('device_data'):
                # Save the uploaded file
                file_path = os.path.join(settings.MEDIA_ROOT, 'vital_signs', f'patient_{patient.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv')
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'wb+') as destination:
                    for chunk in form.cleaned_data['device_data'].chunks():
                        destination.write(chunk)
                
                issue.device_data = os.path.relpath(file_path, settings.BASE_DIR)
            
            issue.save()
            
            # Process vital signs data if available
            if issue.device_data:
                from .utils import process_vital_signs_data
                success = process_vital_signs_data(issue.id, file_path)
                if not success:
                    messages.warning(request, "Your health issue was reported, but there was an error processing the vital signs data.")
            
            messages.success(request, "Your health issue has been reported successfully.")
            return redirect('hospital:doctor_recommendations', issue_id=issue.id)
    else:
        form = IssueForm()
    
    return render(request, 'hospital/create_issue.html', {
        'form': form
    })

@login_required
def doctor_recommendations(request, issue_id):
    """View for recommending doctors based on patient's health issue"""
    # Check if user is a patient using the user_type field
    if not request.user.is_patient():
        messages.error(request, "This page is only for patients.")
        return redirect('dashboard')
    
    # Ensure the patient object exists
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.error(request, "Your patient profile is not set up correctly. Please contact support.")
        return redirect('dashboard')
    
    issue = get_object_or_404(Issue, id=issue_id, patient=patient)
    
    # Get filter parameters
    search_query = request.GET.get('q', None)
    specialization = request.GET.get('specialization', None)
    min_experience = request.GET.get('min_experience', None)
    
    # Base query - find doctors that match the disease type's specialization
    doctors = Doctor.objects.all()
    
    # Apply search if provided
    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) | 
            Q(user__last_name__icontains=search_query)
        )
    # Otherwise, if the issue has a disease type with recommended specialization
    elif issue.disease_type and issue.disease_type.recommended_specialization:
        doctors = doctors.filter(specialization=issue.disease_type.recommended_specialization)
    
    # Apply additional filters
    if specialization:
        doctors = doctors.filter(specialization=specialization)
    
    if min_experience and min_experience.isdigit():
        min_exp_years = int(min_experience)
        doctors = doctors.filter(years_of_experience__gte=min_exp_years)
    
    # Get all distinct specializations for the filter
    all_specializations = Doctor.objects.values_list('specialization', flat=True).distinct()
    
    # If no doctors are found or AI recommendation is explicitly requested, use Gemini API
    ai_recommendations = None
    if (not doctors.exists() or request.GET.get('ai_recommend', False)) and not search_query:
        ai_recommendations = get_ai_doctor_recommendations(issue, Doctor.objects.all())
        # If we have AI recommendations but no filtered doctors, show all doctors
        if ai_recommendations and not doctors.exists():
            doctors = Doctor.objects.all()
    
    return render(request, 'hospital/doctor_recommendations.html', {
        'issue': issue,
        'doctors': doctors,
        'all_specializations': all_specializations,
        'ai_recommendations': ai_recommendations,
        'search_query': search_query
    })

def get_ai_doctor_recommendations(issue, available_doctors):
    """
    Use Google Gemini API to analyze the health issue and recommend doctors
    """
    try:
        # Import the Gemini API library
        import google.generativeai as genai
        import json
        import os
        from dotenv import load_dotenv
        
        # Load environment variables from .env file
        load_dotenv()
        
        # Prepare doctor data
        doctors_data = []
        for doctor in available_doctors:
            doctors_data.append({
                'id': doctor.id,
                'name': f"Dr. {doctor.user.get_full_name()}",
                'specialization': doctor.specialization,
                'years_of_experience': doctor.years_of_experience,
                'bio': doctor.bio if doctor.bio else ""
            })
        
        # Prepare issue data
        issue_data = {
            'type': issue.disease_type.name if issue.disease_type else issue.custom_disease_type,
            'description': issue.description,
            'symptoms': issue.symptoms if issue.symptoms else "",
            'severity': issue.get_severity_display()
        }
        
        # Get API key from .env file using dotenv
        api_key = os.getenv('GEMINI_API_KEY')
        
        # If no API key, fall back to simulation
        if not api_key:
            print("No Gemini API key found in .env file. Falling back to simulated recommendations.")
            return simulate_ai_recommendations(issue_data, doctors_data)
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Select the model
        model = genai.GenerativeModel('gemini-2.0-pro-exp-02-05')
        
        # Build the prompt for Gemini
        prompt = f"""
        You are a medical advisor AI. You need to analyze a patient's health issue and recommend 
        the most suitable doctors from a list of available doctors.
        
        Patient health issue:
        Type: {issue_data['type']}
        Description: {issue_data['description']}
        Symptoms: {issue_data['symptoms']}
        Severity: {issue_data['severity']}
        
        Available doctors:
        {json.dumps(doctors_data, indent=2)}
        
        Please analyze the health issue and provide a list of the top 3 most suitable doctors for this 
        patient, ranked by suitability. For each doctor, provide a brief explanation of why they are 
        recommended. Return the response in the following JSON format:
        {{"recommendations": [
          {{"id": doctor_id, "name": "doctor name", "explanation": "reason for recommendation"}},
          ...
        ]}}
        
        IMPORTANT: Return ONLY valid JSON with no additional text. Make sure the doctor_id is an integer, not a string.
        """
        
        # Generate the response
        response = model.generate_content(prompt)
        
        # Extract and parse the JSON from the response
        response_text = response.text
        
        # Find the JSON part in the response in case there's any additional text
        try:
            # First try to parse the entire response as JSON
            recommendations = json.loads(response_text)
            return recommendations
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the text
            try:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    recommendations = json.loads(json_str)
                    return recommendations
                else:
                    raise ValueError("No JSON found in response")
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing Gemini response: {e}")
                print(f"Response text: {response_text}")
                # Fall back to simulation
                return simulate_ai_recommendations(issue_data, doctors_data)
                
    except Exception as e:
        print(f"Error getting AI recommendations: {e}")
        # Fall back to simulation if there's any error
        return simulate_ai_recommendations(issue_data, doctors_data)

def simulate_ai_recommendations(issue_data, doctors_data):
    """
    Simulate AI recommendations for demo purposes
    """
    if not doctors_data:
        return None
    
    # Create a simulated response based on the issue and available doctors
    recommendations = []
    
    # Sort doctors by experience
    sorted_doctors = sorted(doctors_data, key=lambda x: x['years_of_experience'], reverse=True)
    
    # Simple matching logic based on disease type and specialization
    issue_type = issue_data['type'].lower()
    
    # Map common health issues to likely specializations
    specialization_map = {
        'fever': ['General Medicine', 'Internal Medicine'],
        'cold': ['General Medicine', 'ENT'],
        'flu': ['General Medicine', 'Internal Medicine'],
        'headache': ['Neurology', 'General Medicine'],
        'migraine': ['Neurology'],
        'back pain': ['Orthopedics', 'Neurology', 'Physical Therapy'],
        'skin': ['Dermatology'],
        'rash': ['Dermatology', 'Allergy'],
        'stomach': ['Gastroenterology', 'General Medicine'],
        'digestive': ['Gastroenterology'],
        'heart': ['Cardiology'],
        'blood pressure': ['Cardiology', 'Internal Medicine'],
        'breathing': ['Pulmonology', 'Respiratory Medicine'],
        'respiratory': ['Pulmonology', 'Respiratory Medicine'],
        'eye': ['Ophthalmology'],
        'ear': ['ENT', 'Otolaryngology'],
        'throat': ['ENT', 'Otolaryngology'],
        'joint': ['Orthopedics', 'Rheumatology'],
        'bone': ['Orthopedics'],
        'diabetes': ['Endocrinology', 'Internal Medicine'],
        'thyroid': ['Endocrinology'],
        'anxiety': ['Psychiatry', 'Psychology'],
        'depression': ['Psychiatry', 'Psychology'],
        'sleep': ['Neurology', 'Psychiatry', 'Sleep Medicine'],
        'insomnia': ['Neurology', 'Psychiatry', 'Sleep Medicine'],
        'kidney': ['Nephrology', 'Urology'],
        'urinary': ['Urology', 'Nephrology'],
        'pregnancy': ['Obstetrics', 'Gynecology', 'OB/GYN'],
        'women': ['Gynecology', 'OB/GYN'],
        'child': ['Pediatrics'],
        'cancer': ['Oncology'],
        'surgery': ['General Surgery'],
        'allergy': ['Allergy and Immunology', 'Dermatology'],
        'dental': ['Dentistry'],
        'teeth': ['Dentistry'],
        'checkup': ['General Medicine', 'Family Medicine'],
        'general': ['General Medicine', 'Family Medicine']
    }
    
    # Find matching specializations based on issue type
    matching_specializations = []
    for key, specializations in specialization_map.items():
        if key in issue_type or key in issue_data['description'].lower():
            matching_specializations.extend(specializations)
    
    # Make matching specializations unique
    matching_specializations = list(set(matching_specializations))
    
    # If no matching specialization found, default to General Medicine
    if not matching_specializations:
        matching_specializations = ['General Medicine']
    
    # Find doctors with matching specializations
    matching_doctors = []
    for doctor in sorted_doctors:
        if doctor['specialization'] in matching_specializations:
            matching_doctors.append(doctor)
    
    # If no matching doctors, use all doctors sorted by experience
    if not matching_doctors:
        matching_doctors = sorted_doctors
    
    # Take up to top 3 doctors
    top_doctors = matching_doctors[:3]
    
    # Create recommendations with explanations
    for doctor in top_doctors:
        explanation = f"Dr. {doctor['name']} is recommended based on their specialization in {doctor['specialization']} "
        explanation += f"and {doctor['years_of_experience']} years of experience. "
        
        if doctor['specialization'] in matching_specializations:
            explanation += f"Their expertise in {doctor['specialization']} is well-suited for your health issue."
        else:
            explanation += f"They have significant medical experience that can help address your health concerns."
        
        recommendations.append({
            "id": doctor['id'],
            "name": doctor['name'],
            "explanation": explanation
        })
    
    return {"recommendations": recommendations}

@login_required
def book_appointment(request, doctor_id, issue_id):
    """View for booking an appointment with a doctor"""
    # Check if user is a patient using the user_type field
    if not request.user.is_patient():
        messages.error(request, "Only patients can book appointments.")
        return redirect('dashboard')
    
    # Ensure the patient object exists
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.error(request, "Your patient profile is not set up correctly. Please contact support.")
        return redirect('dashboard')
    
    doctor = get_object_or_404(Doctor, id=doctor_id)
    issue = get_object_or_404(Issue, id=issue_id, patient=patient)
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.doctor = doctor
            appointment.patient = patient
            appointment.issue = issue
            appointment.status = 'scheduled'
            appointment.save()
            
            # Update issue status
            issue.status = 'in_progress'
            issue.save()
            
            messages.success(request, f"Appointment booked successfully with Dr. {doctor.user.get_full_name()} on {appointment.appointment_date} at {appointment.appointment_time}.")
            return redirect('hospital:appointment_detail', appointment_id=appointment.id)
    else:
        form = AppointmentForm()
    
    return render(request, 'hospital/book_appointment.html', {
        'form': form,
        'doctor': doctor,
        'issue': issue
    })

@login_required
def patient_appointments(request):
    """View for patients to see their appointments"""
    # Check if user is a patient using the user_type field
    if not request.user.is_patient():
        messages.error(request, "This page is only for patients.")
        return redirect('dashboard')
    
    # Ensure the patient object exists
    try:
        # Use get_or_create instead of just get to ensure the Patient record exists
        patient, created = Patient.objects.get_or_create(user=request.user)
    except Exception as e:
        messages.error(request, f"Error retrieving your profile: {e}")
        return redirect('dashboard')
    
    # Query for upcoming appointments
    upcoming_queryset = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=timezone.now().date(),
        status='scheduled'
    ).order_by('appointment_date', 'appointment_time')
    
    # Force evaluation by converting to list
    upcoming_appointments = list(upcoming_queryset)
    
    # Query for past appointments
    past_queryset = Appointment.objects.filter(
        patient=patient
    ).filter(
        Q(appointment_date__lt=timezone.now().date()) | 
        ~Q(status='scheduled')
    ).order_by('-appointment_date', '-appointment_time')
    
    # Force evaluation by converting to list
    past_appointments = list(past_queryset)
    
    # Debug information
    print(f"Patient {patient.id}: Found {len(upcoming_appointments)} upcoming appointments and {len(past_appointments)} past appointments")
    
    return render(request, 'hospital/patient_appointments.html', {
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments
    })

@login_required
def doctor_appointments(request):
    """View for doctors to see their appointments"""
    # Check if user is a doctor using the user_type field
    if not request.user.is_doctor():
        messages.error(request, "This page is only for doctors.")
        return redirect('dashboard')
    
    # Ensure the doctor object exists
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "Your doctor profile is not set up correctly. Please contact support.")
        return redirect('dashboard')
    
    # Query for upcoming appointments
    upcoming_queryset = Appointment.objects.filter(
        doctor=doctor,
        appointment_date__gte=timezone.now().date(),
        status='scheduled'
    ).order_by('appointment_date', 'appointment_time')
    
    # Force evaluation by converting to list
    upcoming_appointments = list(upcoming_queryset)
    
    # Query for past appointments
    past_queryset = Appointment.objects.filter(
        doctor=doctor
    ).filter(
        Q(appointment_date__lt=timezone.now().date()) | 
        ~Q(status='scheduled')
    ).order_by('-appointment_date', '-appointment_time')
    
    # Force evaluation by converting to list
    past_appointments = list(past_queryset)
    
    # Today's appointments - create from the list
    today = timezone.now().date()
    today_appointments = [appt for appt in upcoming_appointments if appt.appointment_date == today]
    
    # Debug information
    print(f"Doctor {doctor.id}: Found {len(upcoming_appointments)} upcoming appointments, {len(today_appointments)} today")
    
    return render(request, 'hospital/doctor_appointments.html', {
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'today_appointments': today_appointments
    })

@login_required
def appointment_detail(request, appointment_id):
    """View for appointment details"""
    # Determine if the user is a doctor or patient and retrieve the appropriate object
    if request.user.is_doctor():
        try:
            doctor = Doctor.objects.get(user=request.user)
            appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)
        except Doctor.DoesNotExist:
            messages.error(request, "Your doctor profile is not set up correctly.")
            return redirect('dashboard')
    elif request.user.is_patient():
        try:
            patient = Patient.objects.get(user=request.user)
            appointment = get_object_or_404(Appointment, id=appointment_id, patient=patient)
        except Patient.DoesNotExist:
            messages.error(request, "Your patient profile is not set up correctly.")
            return redirect('dashboard')
    else:
        messages.error(request, "You don't have permission to view this appointment.")
        return redirect('dashboard')
    
    # Get medical summary for doctors
    medical_summary = None
    if request.user.is_doctor() and appointment.patient:
        patient_issues = Issue.objects.filter(patient=appointment.patient).order_by('-created_at')
        medical_summary = generate_medical_summary(patient_issues)
    
    return render(request, 'hospital/appointment_detail.html', {
        'appointment': appointment,
        'medical_summary': medical_summary
    })

@login_required
def patient_medical_history(request, patient_id=None):
    """View for patient medical history"""
    if patient_id:
        # Doctor viewing a patient's history
        if not request.user.is_doctor():
            messages.error(request, "Only doctors can view patient records.")
            return redirect('dashboard')
        
        patient = get_object_or_404(Patient, id=patient_id)
        is_self_view = False
        
        # Check if the doctor has treated this patient
        try:
            doctor = Doctor.objects.get(user=request.user)
            has_treated = Appointment.objects.filter(
                doctor=doctor,
                patient=patient
            ).exists()
        except Doctor.DoesNotExist:
            has_treated = False
        
        if not has_treated and not request.user.is_staff:
            messages.error(request, "You don't have permission to view this patient's history.")
            return redirect('dashboard')
        
        # Get all patient issues for the AI summary
        issues = Issue.objects.filter(patient=patient).order_by('-created_at')
        
        # Generate the AI medical summary using Gemini
        medical_summary = generate_medical_summary(issues)
        
    else:
        # Patient viewing their own history
        if not request.user.is_patient():
            messages.error(request, "This page is only for patients.")
            return redirect('dashboard')
        
        # Ensure the patient object exists
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            messages.error(request, "Your patient profile is not set up correctly. Please contact support.")
            return redirect('dashboard')
            
        is_self_view = True
        
        # Get issues and generate AI summary for patient's self-view
        issues = Issue.objects.filter(patient=patient).order_by('-created_at')
        medical_summary = generate_medical_summary(issues) if issues.exists() else None
    
    return render(request, 'hospital/patient_medical_history.html', {
        'patient': patient,
        'issues': issues,
        'is_self_view': is_self_view,
        'medical_summary': medical_summary
    })

@login_required
def doctor_patients(request):
    """View for doctors to see their patients"""
    # Check if user is a doctor using the user_type field
    if not request.user.is_doctor():
        messages.error(request, "This page is only for doctors.")
        return redirect('dashboard')
    
    # Ensure the doctor object exists
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "Your doctor profile is not set up correctly. Please contact support.")
        return redirect('dashboard')
    
    # Get patients who have appointments with this doctor
    patients = Patient.objects.filter(
        appointments__doctor=doctor
    ).distinct()
    
    return render(request, 'hospital/doctor_patients.html', {
        'patients': patients
    })

@login_required
def browse_doctors(request):
    """View for browsing all doctors in the system"""
    # Check if user is a patient using the user_type field
    if not request.user.is_patient():
        messages.error(request, "This page is only for patients.")
        return redirect('dashboard')
    
    # Ensure the patient object exists
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.error(request, "Your patient profile is not set up correctly. Please contact support.")
        return redirect('dashboard')
    
    # Get filter parameters
    search_query = request.GET.get('q', None)
    specialization = request.GET.get('specialization', None)
    min_experience = request.GET.get('min_experience', None)
    issue_id = request.GET.get('issue_id', None)
    
    # Check if an existing issue ID was provided
    existing_issue = None
    if issue_id:
        try:
            existing_issue = Issue.objects.get(id=issue_id, patient=patient)
            if existing_issue.status != 'open':
                existing_issue = None
                messages.info(request, "The selected health issue is already being addressed.")
        except Issue.DoesNotExist:
            messages.warning(request, "The specified health issue was not found.")
    
    # Start with all doctors
    doctors = Doctor.objects.all()
    
    # Apply search if provided
    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) | 
            Q(user__last_name__icontains=search_query) | 
            Q(specialization__icontains=search_query)
        )
    
    # Apply additional filters
    if specialization:
        doctors = doctors.filter(specialization=specialization)
    
    if min_experience and min_experience.isdigit():
        min_exp_years = int(min_experience)
        doctors = doctors.filter(years_of_experience__gte=min_exp_years)
    
    # Get all distinct specializations for the filter
    all_specializations = Doctor.objects.values_list('specialization', flat=True).distinct()
    
    form = DoctorFilterForm(request.GET)
    
    return render(request, 'hospital/browse_doctors.html', {
        'doctors': doctors,
        'all_specializations': all_specializations,
        'filter_form': form,
        'search_query': search_query,
        'existing_issue': existing_issue
    })

@login_required
def direct_book_appointment(request, doctor_id):
    """View for booking an appointment with a doctor without an existing issue"""
    # Check if user is a patient using the user_type field
    if not request.user.is_patient():
        messages.error(request, "Only patients can book appointments.")
        return redirect('dashboard')
    
    # Ensure the patient object exists
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.error(request, "Your patient profile is not set up correctly. Please contact support.")
        return redirect('dashboard')
    
    doctor = get_object_or_404(Doctor, id=doctor_id)
    
    # Check if an existing issue ID was provided
    existing_issue = None
    issue_id = request.GET.get('issue_id')
    if issue_id:
        try:
            existing_issue = Issue.objects.get(id=issue_id, patient=patient)
        except Issue.DoesNotExist:
            messages.warning(request, "The specified health issue was not found. Please create a new one.")
    
    if request.method == 'POST':
        # If using an existing issue, we don't need the issue form
        if existing_issue:
            appointment_form = AppointmentForm(request.POST)
            issue_form = None
            
            if appointment_form.is_valid():
                appointment = appointment_form.save(commit=False)
                appointment.doctor = doctor
                appointment.patient = patient
                appointment.issue = existing_issue
                appointment.status = 'scheduled'
                appointment.save()
                
                # Update issue status
                existing_issue.status = 'in_progress'
                existing_issue.save()
                
                messages.success(request, f"Appointment booked successfully with Dr. {doctor.user.get_full_name()} on {appointment.appointment_date} at {appointment.appointment_time}.")
                return redirect('hospital:appointment_detail', appointment_id=appointment.id)
        else:
            # No existing issue, need both forms
            issue_form = IssueForm(request.POST)
            appointment_form = AppointmentForm(request.POST)
            
            if issue_form.is_valid() and appointment_form.is_valid():
                # First save the issue
                issue = issue_form.save(commit=False)
                issue.patient = patient
                
                # Handle device data
                if issue_form.cleaned_data.get('device_data'):
                    # In a real application, this would be a file upload
                    # For this example, we're using the existing CSV in the datasets folder
                    issue.device_data = 'datasets/human_vital_signs_dataset_2024.csv'
                    
                issue.save()
                
                # Then save the appointment
                appointment = appointment_form.save(commit=False)
                appointment.doctor = doctor
                appointment.patient = patient
                appointment.issue = issue
                appointment.status = 'scheduled'
                appointment.save()
                
                # Update issue status
                issue.status = 'in_progress'
                issue.save()
                
                messages.success(request, f"Appointment booked successfully with Dr. {doctor.user.get_full_name()} on {appointment.appointment_date} at {appointment.appointment_time}.")
                return redirect('hospital:appointment_detail', appointment_id=appointment.id)
    else:
        appointment_form = AppointmentForm()
        issue_form = None if existing_issue else IssueForm()
    
    return render(request, 'hospital/direct_book_appointment.html', {
        'issue_form': issue_form,
        'appointment_form': appointment_form,
        'doctor': doctor,
        'existing_issue': existing_issue
    })

@login_required
def visualize_vital_signs(request, issue_id=None):
    """View for visualizing vital signs data"""
    # Check if user is a doctor or patient
    if not (request.user.is_doctor() or request.user.is_patient() or request.user.is_staff):
        messages.error(request, "You don't have permission to view this page.")
        return redirect('dashboard')
    
    issue = None
    patient = None
    
    if issue_id:
        # Get the issue
        try:
            if request.user.is_doctor():
                # Doctor can view any patient's issue if they have an appointment
                doctor = Doctor.objects.get(user=request.user)
                issue = get_object_or_404(
                    Issue, 
                    id=issue_id, 
                    patient__appointments__doctor=doctor
                )
            elif request.user.is_patient():
                # Patient can only view their own issues
                patient = Patient.objects.get(user=request.user)
                issue = get_object_or_404(Issue, id=issue_id, patient=patient)
            elif request.user.is_staff:
                # Staff can view any issue
                issue = get_object_or_404(Issue, id=issue_id)
            
            patient = issue.patient
        except Exception as e:
            messages.error(request, f"Error retrieving issue: {e}")
            return redirect('dashboard')
    elif request.user.is_patient():
        # If no issue_id is provided and user is a patient, use their ID
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            messages.error(request, "Your patient profile is not set up correctly.")
            return redirect('dashboard')
    
    # If this issue has device data
    has_device_data = issue and issue.device_data
    
    # Get patient ID for vital signs data
    patient_id = request.GET.get('patient_id')
    if not patient_id and patient:
        patient_id = str(patient.id)
    
    # Get dataset path
    dataset_path = None
    if has_device_data:
        # In a real app, this would be the actual uploaded file
        # For this example, we're using the demo dataset
        dataset_path = os.path.join(settings.BASE_DIR, issue.device_data)
    else:
        # Use the demo dataset
        dataset_path = os.path.join(settings.BASE_DIR, 'datasets/human_vital_signs_dataset_2024.csv')
    
    # Check if dataset exists
    if not os.path.exists(dataset_path):
        messages.error(request, "Vital signs dataset not found.")
        return redirect('dashboard')
    
    # Get tab to display
    active_tab = request.GET.get('tab', 'dashboard')
    
    return render(request, 'hospital/vital_signs_visualization.html', {
        'issue': issue,
        'patient': patient,
        'patient_id': patient_id,
        'dataset_path': dataset_path,
        'has_device_data': has_device_data,
        'active_tab': active_tab
    })

@login_required
def vital_signs_data(request):
    """API view to get vital signs plots as JSON"""
    # Check if user is a doctor or patient
    if not (request.user.is_doctor() or request.user.is_patient() or request.user.is_staff):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Get patient ID and dataset path from request
    patient_id = request.GET.get('patient_id')
    dataset_path = request.GET.get('dataset_path')
    
    # Get time range filter parameters
    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')
    
    if not dataset_path:
        return JsonResponse({'error': 'Dataset path not provided'}, status=400)
    
    # Check if file exists
    if not os.path.exists(dataset_path):
        return JsonResponse({'error': 'Dataset file not found'}, status=404)
    
    # Generate plots with optional time filtering
    plot_data = generate_vital_signs_plots(dataset_path, patient_id, start_time, end_time)
    
    if plot_data is None:
        return JsonResponse({'error': 'Error generating plots'}, status=500)
    
    return JsonResponse(plot_data)

@login_required
def vital_signs_dashboard(request, issue_id=None):
    context = {}
    
    if request.user.is_doctor():
        try:
            doctor = Doctor.objects.get(user=request.user)
            context['has_new_alerts'] = Alert.objects.filter(doctor=doctor, status='new').exists()
        except Doctor.DoesNotExist:
            context['has_new_alerts'] = False
    
    # Get issue and patient if issue_id is provided
    if issue_id:
        try:
            issue = get_object_or_404(Issue, id=issue_id)
            patient = issue.patient
        except Http404:
            messages.error(request, "Issue not found or you don't have permission to view it.")
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"Error retrieving issue: {str(e)}")
            return redirect('dashboard')
    elif request.user.is_patient():
        try:
            patient = get_object_or_404(Patient, user=request.user)
        except Http404:
            messages.error(request, "Your patient profile is not set up correctly.")
            return redirect('dashboard')
    
    context.update({
        'issue': issue if 'issue' in locals() else None,
        'patient': patient if 'patient' in locals() else None,
        'page_title': f"Vital Signs Dashboard - {patient.user.get_full_name() if 'patient' in locals() else 'All Patients'}"
    })
    
    return render(request, 'hospital/vital_signs_dashboard.html', context)

@login_required
def doctor_alerts(request):
    """View for doctors to see their alerts"""
    from hospital.utils import reprocess_vital_signs_files
    reprocess_vital_signs_files()
    if not request.user.is_doctor():
        messages.error(request, "This page is only for doctors.")
        return redirect('dashboard')
    
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "Your doctor profile is not set up correctly.")
        return redirect('dashboard')
    
    # Get alerts for this doctor
    alerts = Alert.objects.filter(doctor=doctor).select_related('patient__user', 'issue')
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        alerts = alerts.filter(status=status)
    
    # Mark alerts as viewed
    if request.method == 'POST':
        alert_id = request.POST.get('alert_id')
        action = request.POST.get('action')
        
        if alert_id and action:
            try:
                alert = alerts.get(id=alert_id)
                if action == 'acknowledge':
                    alert.status = 'acknowledged'
                elif action == 'resolve':
                    alert.status = 'resolved'
                alert.save()
                messages.success(request, f"Alert {action}d successfully.")
            except Alert.DoesNotExist:
                messages.error(request, "Alert not found.")
    
    # Update any unviewed alerts to viewed status
    alerts.filter(status='new').update(status='viewed')
    
    # Group alerts by urgency for the template
    grouped_alerts = {
        'critical': alerts.filter(urgency='critical'),
        'high': alerts.filter(urgency='high'),
        'medium': alerts.filter(urgency='medium'),
        'low': alerts.filter(urgency='low')
    }
    
    return render(request, 'hospital/doctor_alerts.html', {
        'grouped_alerts': grouped_alerts,
        'selected_status': status
    })
