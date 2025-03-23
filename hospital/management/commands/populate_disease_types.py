from django.core.management.base import BaseCommand
from django.db import transaction
from hospital.models import DiseaseType


class Command(BaseCommand):
    help = 'Populates the database with common disease types'

    def handle(self, *args, **options):
        self.stdout.write('Starting disease type population...')
        
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
        
        specializations = {
            'Fever': 'General Medicine',
            'Cold and Flu': 'General Medicine',
            'Headache': 'Neurology',
            'Allergies': 'Allergy and Immunology',
            'Stomach Pain': 'Gastroenterology',
            'Back Pain': 'Orthopedics',
            'Joint Pain': 'Rheumatology',
            'Skin Rash': 'Dermatology',
            'Respiratory Issues': 'Pulmonology',
            'Eye Problems': 'Ophthalmology',
            'Ear Infection': 'Otolaryngology',
            'Dental Issues': 'Dentistry',
            'Urinary Tract Infection': 'Urology',
            'High Blood Pressure': 'Cardiology',
            'Diabetes': 'Endocrinology',
            'Anxiety': 'Psychiatry',
            'Depression': 'Psychiatry',
            'Insomnia': 'Sleep Medicine',
            'Digestive Issues': 'Gastroenterology',
            'General Checkup': 'General Medicine'
        }
        
        descriptions = {
            'Fever': 'Elevated body temperature, often accompanied by chills and body aches.',
            'Cold and Flu': 'Viral infections causing sore throat, cough, runny nose, and body aches.',
            'Headache': 'Pain or discomfort in the head, scalp, or neck region.',
            'Allergies': 'Immune system reaction to substances that are normally harmless.',
            'Stomach Pain': 'Discomfort or pain in the abdominal region.',
            'Back Pain': 'Pain affecting the back, often in the lower spine area.',
            'Joint Pain': 'Discomfort, aches, or soreness in joints.',
            'Skin Rash': 'Inflammation or discoloration of the skin.',
            'Respiratory Issues': 'Problems with breathing or the respiratory system.',
            'Eye Problems': 'Issues affecting vision or the eyes.',
            'Ear Infection': 'Inflammation or infection of the ear.',
            'Dental Issues': 'Problems with teeth, gums, or oral health.',
            'Urinary Tract Infection': 'Infection affecting the urinary system.',
            'High Blood Pressure': 'Elevated blood pressure in the arteries.',
            'Diabetes': 'Metabolic disorder affecting blood sugar regulation.',
            'Anxiety': 'Feelings of worry, nervousness, or unease.',
            'Depression': 'Persistent feeling of sadness and loss of interest.',
            'Insomnia': 'Difficulty falling or staying asleep.',
            'Digestive Issues': 'Problems with digestion or the digestive system.',
            'General Checkup': 'Routine health examination without specific complaints.'
        }
        
        with transaction.atomic():
            created_count = 0
            for type_name in common_types:
                obj, created = DiseaseType.objects.get_or_create(
                    name=type_name,
                    defaults={
                        'description': descriptions.get(type_name, ''),
                        'recommended_specialization': specializations.get(type_name, 'General Medicine')
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(f'Created {created_count} new disease types')
        self.stdout.write(f'Total disease types: {DiseaseType.objects.count()}')
        self.stdout.write(self.style.SUCCESS('Common disease types populated successfully!')) 