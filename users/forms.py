from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.db import transaction
from .models import User, DoctorProfile, PatientProfile


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Username'}
    ))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={'class': 'form-control', 'placeholder': 'Password'}
    ))


class DoctorSignUpForm(UserCreationForm):
    first_name = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'First Name'}
    ))
    last_name = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Last Name'}
    ))
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={'class': 'form-control', 'placeholder': 'Email'}
    ))
    phone_number = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Phone Number'}
    ))
    date_of_birth = forms.DateField(widget=forms.DateInput(
        attrs={'class': 'form-control', 'type': 'date'}
    ))
    address = forms.CharField(widget=forms.Textarea(
        attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3}
    ))
    specialization = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Specialization'}
    ))
    license_number = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'License Number'}
    ))
    years_of_experience = forms.IntegerField(widget=forms.NumberInput(
        attrs={'class': 'form-control', 'placeholder': 'Years of Experience'}
    ))
    bio = forms.CharField(required=False, widget=forms.Textarea(
        attrs={'class': 'form-control', 'placeholder': 'Professional Bio', 'rows': 4}
    ))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 
                  'date_of_birth', 'address', 'password1', 'password2']
    
    @transaction.atomic
    def save(self):
        user = super().save(commit=False)
        user.user_type = 'doctor'
        user.email = self.cleaned_data.get('email')
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.phone_number = self.cleaned_data.get('phone_number')
        user.date_of_birth = self.cleaned_data.get('date_of_birth')
        user.address = self.cleaned_data.get('address')
        user.save()
        
        doctor_profile = DoctorProfile.objects.create(
            user=user,
            specialization=self.cleaned_data.get('specialization'),
            license_number=self.cleaned_data.get('license_number'),
            years_of_experience=self.cleaned_data.get('years_of_experience'),
            bio=self.cleaned_data.get('bio')
        )
        
        return user


class PatientSignUpForm(UserCreationForm):
    first_name = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'First Name'}
    ))
    last_name = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Last Name'}
    ))
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={'class': 'form-control', 'placeholder': 'Email'}
    ))
    phone_number = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Phone Number'}
    ))
    date_of_birth = forms.DateField(widget=forms.DateInput(
        attrs={'class': 'form-control', 'type': 'date'}
    ))
    address = forms.CharField(widget=forms.Textarea(
        attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3}
    ))
    blood_group = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Blood Group'}
    ))
    emergency_contact_name = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Emergency Contact Name'}
    ))
    emergency_contact_number = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Emergency Contact Number'}
    ))
    allergies = forms.CharField(required=False, widget=forms.Textarea(
        attrs={'class': 'form-control', 'placeholder': 'Known Allergies', 'rows': 3}
    ))
    medical_history = forms.CharField(required=False, widget=forms.Textarea(
        attrs={'class': 'form-control', 'placeholder': 'Medical History', 'rows': 4}
    ))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 
                  'date_of_birth', 'address', 'password1', 'password2']
    
    @transaction.atomic
    def save(self):
        user = super().save(commit=False)
        user.user_type = 'patient'
        user.email = self.cleaned_data.get('email')
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.phone_number = self.cleaned_data.get('phone_number')
        user.date_of_birth = self.cleaned_data.get('date_of_birth')
        user.address = self.cleaned_data.get('address')
        user.save()
        
        patient_profile = PatientProfile.objects.create(
            user=user,
            blood_group=self.cleaned_data.get('blood_group'),
            emergency_contact_name=self.cleaned_data.get('emergency_contact_name'),
            emergency_contact_number=self.cleaned_data.get('emergency_contact_number'),
            allergies=self.cleaned_data.get('allergies'),
            medical_history=self.cleaned_data.get('medical_history')
        )
        
        return user 