from django.shortcuts import render, redirect
from django.views.generic import CreateView, TemplateView
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.auth.views import LoginView

from .forms import DoctorSignUpForm, PatientSignUpForm, UserLoginForm
from .models import User, DoctorProfile, PatientProfile


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
        
        if user.is_doctor():
            context['doctor_profile'] = DoctorProfile.objects.get(user=user)
            context['is_doctor'] = True
        elif user.is_patient():
            context['patient_profile'] = PatientProfile.objects.get(user=user)
            context['is_patient'] = True
            
        return context


@login_required
def profile_view(request):
    user = request.user
    
    if user.is_doctor():
        doctor_profile = DoctorProfile.objects.get(user=user)
        return render(request, 'users/doctor_profile.html', {'profile': doctor_profile})
    elif user.is_patient():
        patient_profile = PatientProfile.objects.get(user=user)
        return render(request, 'users/patient_profile.html', {'profile': patient_profile})
