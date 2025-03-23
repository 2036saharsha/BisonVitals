from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.db import transaction
from .models import User, DoctorProfile, PatientProfile
from hospital.models import Doctor, Patient


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
        
        # Create DoctorProfile - use get_or_create to avoid duplicate issues
        doctor_profile, created = DoctorProfile.objects.get_or_create(
            user=user,
            defaults={
                'specialization': self.cleaned_data.get('specialization'),
                'license_number': self.cleaned_data.get('license_number'),
                'years_of_experience': self.cleaned_data.get('years_of_experience'),
                'bio': self.cleaned_data.get('bio')
            }
        )
        
        # If profile exists but fields are different, update them
        if not created:
            doctor_profile.specialization = self.cleaned_data.get('specialization')
            doctor_profile.license_number = self.cleaned_data.get('license_number')
            doctor_profile.years_of_experience = self.cleaned_data.get('years_of_experience')
            doctor_profile.bio = self.cleaned_data.get('bio')
            doctor_profile.save()
        
        # Create Doctor record - use get_or_create to avoid duplicate issues
        Doctor.objects.get_or_create(
            user=user,
            defaults={
                'specialization': self.cleaned_data.get('specialization'),
                'license_number': self.cleaned_data.get('license_number'),
                'years_of_experience': self.cleaned_data.get('years_of_experience'),
                'bio': self.cleaned_data.get('bio')
            }
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
        
        # Create PatientProfile
        patient_profile = PatientProfile.objects.create(
            user=user,
            blood_group=self.cleaned_data.get('blood_group'),
            emergency_contact_name=self.cleaned_data.get('emergency_contact_name'),
            emergency_contact_number=self.cleaned_data.get('emergency_contact_number'),
            allergies=self.cleaned_data.get('allergies'),
            medical_history=self.cleaned_data.get('medical_history')
        )
        
        # Create Patient record - use get_or_create to avoid duplicate issues
        Patient.objects.get_or_create(
            user=user,
            defaults={
                'date_of_birth': self.cleaned_data.get('date_of_birth'),
                'blood_group': self.cleaned_data.get('blood_group'),
                'allergies': self.cleaned_data.get('allergies'),
                'emergency_contact_name': self.cleaned_data.get('emergency_contact_name'),
                'emergency_contact_number': self.cleaned_data.get('emergency_contact_number')
            }
        )
        
        return user 


class DoctorProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    address = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    specialization = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    license_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    years_of_experience = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}))
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

    class Meta:
        model = DoctorProfile
        fields = ['specialization', 'license_number', 'years_of_experience', 'bio']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            self.fields['phone_number'].initial = self.instance.user.phone_number
            self.fields['date_of_birth'].initial = self.instance.user.date_of_birth
            self.fields['address'].initial = self.instance.user.address

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            # Update User model fields
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.phone_number = self.cleaned_data['phone_number']
            user.date_of_birth = self.cleaned_data['date_of_birth']
            user.address = self.cleaned_data['address']
            user.save()
            
            profile.save()
        return profile 