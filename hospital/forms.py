from django import forms
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Issue, Appointment, DiseaseType
from users.models import DoctorProfile

class DateInput(forms.DateInput):
    input_type = 'date'

class TimeInput(forms.TimeInput):
    input_type = 'time'

class IssueForm(forms.ModelForm):
    """Form for patients to report health issues"""
    custom_disease_type = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specify if not in the list above'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your symptoms and health issue'})
    )
    symptoms = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'List your symptoms'}),
        required=False
    )
    device_data = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Link my health device data",
        help_text="Link data from your health monitoring device for the doctor to view"
    )
    
    class Meta:
        model = Issue
        fields = ['disease_type', 'custom_disease_type', 'description', 'symptoms', 'severity', 'device_data']
        widgets = {
            'disease_type': forms.Select(attrs={'class': 'form-control'}),
            'severity': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make sure we have common disease types in the database
        self.ensure_common_disease_types()
        
        # Set the disease_type field label
        self.fields['disease_type'].label = "What type of issue are you experiencing?"
        self.fields['disease_type'].empty_label = "Select from common issues:"
        
        # Help text for custom issue
        self.fields['custom_disease_type'].label = "Other issue type"
        self.fields['custom_disease_type'].help_text = "If your issue is not in the list above, please specify here."
    
    def ensure_common_disease_types(self):
        """Ensures that common disease types exist in the database"""
        common_types = DiseaseType.get_common_types()
        for type_name in common_types:
            DiseaseType.objects.get_or_create(name=type_name)

    def clean(self):
        cleaned_data = super().clean()
        disease_type = cleaned_data.get('disease_type')
        custom_disease_type = cleaned_data.get('custom_disease_type')
        
        # Require either a disease_type or a custom_disease_type
        if not disease_type and not custom_disease_type:
            raise forms.ValidationError("Please either select an issue type or specify a custom one.")
        
        return cleaned_data

class AppointmentForm(forms.ModelForm):
    """Form for booking appointments"""
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any additional information for the doctor'}),
        required=False
    )
    
    class Meta:
        model = Appointment
        fields = ['appointment_date', 'appointment_time', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'min': 'today'}),
            'appointment_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(AppointmentForm, self).__init__(*args, **kwargs)
        # Set default date to a week from now
        self.fields['appointment_date'].initial = timezone.now().date() + timedelta(days=7)
        
        # Set default time to 9:00 AM
        self.fields['appointment_time'].initial = '09:00'
    
    def clean_appointment_date(self):
        date = self.cleaned_data['appointment_date']
        if date < timezone.now().date():
            raise forms.ValidationError("Appointment date cannot be in the past.")
        
        # Check if the date is a weekend (5=Saturday, 6=Sunday)
        if date.weekday() >= 5:
            raise forms.ValidationError("Appointments cannot be scheduled on weekends.")
        
        return date
    
    def clean_appointment_time(self):
        time = self.cleaned_data['appointment_time']
        
        # Check if the time is within business hours (9 AM to 5 PM)
        business_start = datetime.strptime('09:00', '%H:%M').time()
        business_end = datetime.strptime('17:00', '%H:%M').time()
        
        if time < business_start or time > business_end:
            raise forms.ValidationError("Appointments must be scheduled between 9:00 AM and 5:00 PM.")
            
        return time

class DoctorFilterForm(forms.Form):
    specialization = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    years_of_experience = forms.ChoiceField(
        choices=[
            ('', 'Any Experience'),
            ('0,2', '0-2 years'),
            ('3,5', '3-5 years'),
            ('5,10', '5-10 years'),
            ('10,100', '10+ years'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        specializations = DoctorProfile.objects.values_list('specialization', flat=True).distinct()
        specialization_choices = [('', 'All Specializations')]
        specialization_choices.extend([(spec, spec) for spec in specializations if spec])
        self.fields['specialization'].choices = specialization_choices 