from django.shortcuts import render, redirect
from django.views.generic import CreateView, TemplateView
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.auth.views import LoginView
from django.utils import timezone
from django.db.models import Q

from .forms import DoctorSignUpForm, PatientSignUpForm, UserLoginForm
from .models import User, DoctorProfile, PatientProfile

# Import these at the module level
from hospital.models import Patient, Appointment, Doctor


class HomeView(TemplateView):
    template_name = 'users/home.html'


class CustomLoginView(LoginView):
    form_class = UserLoginForm
    template_name = 'users/login.html'
    
    def get_success_url(self):
        return reverse_lazy('dashboard')


class SignUpView(TemplateView):
    template_name = 'users/signup.html'


class DoctorSignUpView(CreateView):
    model = User
    form_class = DoctorSignUpForm
    template_name = 'users/doctor_signup.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('dashboard')


class PatientSignUpView(CreateView):
    model = User
    form_class = PatientSignUpForm
    template_name = 'users/patient_signup.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('dashboard')


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'users/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Initialize debug variables - make sure these are integers not None
        context['upcoming_appointments'] = []
        context['debug_appointment_count'] = 0
        
        if user.is_doctor():
            context['doctor_profile'] = DoctorProfile.objects.get(user=user)
            context['is_doctor'] = True
            
            # Get doctor's upcoming appointments
            try:
                # Get doctor record
                doctor = Doctor.objects.get(user=user)
                
                # Simple approach - get the count first
                appointments_count = Appointment.objects.filter(
                    doctor=doctor,
                    appointment_date__gte=timezone.now().date(),
                    status='scheduled'
                ).count()
                
                # Set the count immediately
                context['debug_appointment_count'] = appointments_count
                
                if appointments_count > 0:
                    # Only get the full objects if there are appointments
                    doctor_appointments = list(Appointment.objects.filter(
                        doctor=doctor,
                        appointment_date__gte=timezone.now().date(),
                        status='scheduled'
                    ).order_by('appointment_date', 'appointment_time'))
                    
                    context['upcoming_appointments'] = doctor_appointments
                
                print(f"Doctor {doctor.id}: Found {appointments_count} upcoming appointments")
                print(f"Final context data: {context['debug_appointment_count']} appointments")
                
            except Exception as e:
                print(f"Error fetching doctor appointments: {e}")
                context['upcoming_appointments'] = []
                context['debug_appointment_count'] = 0
                
        elif user.is_patient():
            context['patient_profile'] = PatientProfile.objects.get(user=user)
            context['is_patient'] = True
            
            # Get patient's upcoming appointments
            try:
                # Get or create patient record
                patient, created = Patient.objects.get_or_create(user=user)
                
                # Simple approach - get the count first
                appointments_count = Appointment.objects.filter(
                    patient=patient,
                    appointment_date__gte=timezone.now().date(),
                    status='scheduled'
                ).count()
                
                # Set the count immediately
                context['debug_appointment_count'] = appointments_count
                
                if appointments_count > 0:
                    # Only get the full objects if there are appointments
                    upcoming_appointments = list(Appointment.objects.filter(
                        patient=patient,
                        appointment_date__gte=timezone.now().date(),
                        status='scheduled'
                    ).order_by('appointment_date', 'appointment_time'))
                    
                    context['upcoming_appointments'] = upcoming_appointments
                
                print(f"Patient {patient.id}: Found {appointments_count} upcoming appointments")
                print(f"Final context data: {context['debug_appointment_count']} appointments")
                
            except Exception as e:
                print(f"Error fetching appointments: {e}")
                context['upcoming_appointments'] = []
                context['debug_appointment_count'] = 0
            
        return context


@login_required
def profile_view(request):
    user = request.user
    
    if user.is_doctor():
        doctor_profile = DoctorProfile.objects.get(user=user)
        
        # Get doctor's upcoming appointments
        try:
            # Get doctor record
            doctor = Doctor.objects.get(user=user)
            
            # Query for upcoming appointments
            appointments_queryset = Appointment.objects.filter(
                doctor=doctor,
                appointment_date__gte=timezone.now().date(),
                status='scheduled'
            ).order_by('appointment_date', 'appointment_time')
            
            # Force evaluation by converting to list
            upcoming_appointments = list(appointments_queryset)
            
            # Debug information
            print(f"Profile View - Doctor {doctor.id}: Found {len(upcoming_appointments)} upcoming appointments")
        except Exception as e:
            print(f"Error fetching appointments in doctor profile view: {e}")
            upcoming_appointments = []
            
        return render(request, 'users/doctor_profile.html', {
            'profile': doctor_profile,
            'upcoming_appointments': upcoming_appointments
        })
        
    elif user.is_patient():
        patient_profile = PatientProfile.objects.get(user=user)
        
        # Get patient's upcoming appointments
        try:
            # Get or create patient record
            patient, created = Patient.objects.get_or_create(user=user)
            
            # Query for upcoming appointments
            appointments_queryset = Appointment.objects.filter(
                patient=patient,
                appointment_date__gte=timezone.now().date(),
                status='scheduled'
            ).order_by('appointment_date', 'appointment_time')
            
            # Force evaluation by converting to list
            upcoming_appointments = list(appointments_queryset)
            
            # Debug information
            print(f"Profile View - Patient {patient.id}: Found {len(upcoming_appointments)} upcoming appointments")
        except Exception as e:
            print(f"Error fetching appointments in profile view: {e}")
            upcoming_appointments = []
            
        return render(request, 'users/patient_profile.html', {
            'profile': patient_profile,
            'upcoming_appointments': upcoming_appointments
        })
