import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
import os
import pickle

from .models import Alert, Issue, Doctor, Patient

def process_vital_signs_data(issue_id, file_path, start_time=None):
    """Process vital signs data and create alerts for anomalies"""
    try:
        # Load the model with correct filename
        model_path = os.path.join(settings.BASE_DIR, 'hospital', 'ml_models', 'vitals-model.pkl')
        if not os.path.exists(model_path):
            print(f"Model not found at {model_path}")
            return False

        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        print(f"Successfully loaded model from {model_path}")
        
        # Get the issue and related objects
        issue = Issue.objects.get(id=issue_id)
        patient = issue.patient
        doctors = Doctor.objects.filter(appointments__patient=patient).distinct()
        
        if not doctors.exists():
            print(f"No doctors found for patient {patient.id}")
            return False
        
        # Read and preprocess the data
        df = pd.read_csv(file_path)
        print(f"Loaded data with {len(df)} rows and columns: {df.columns.tolist()}")
        
        # If start_time is not provided, use current time
        current_time = timezone.now()
        if not start_time:
            start_time = current_time
        
        # Make predictions if Risk Category column doesn't exist
        if 'Risk Category' not in df.columns:
            # Prepare features for the model - match the exact names from the notebook
            required_features = [
                'Heart Rate', 'Respiratory Rate', 'Body Temperature', 'Oxygen Saturation',
                'Systolic Blood Pressure', 'Diastolic Blood Pressure', 'Age', 'Gender',
                'Weight (kg)', 'Height (m)', 'Derived_HRV', 'Derived_Pulse_Pressure',
                'Derived_BMI', 'Derived_MAP'
            ]
            
            # Print current columns for debugging
            print(f"Current columns in CSV: {df.columns.tolist()}")
            
            # Add patient demographic data if not in CSV
            if 'Age' not in df.columns:
                df['Age'] = getattr(patient.user, 'age', 30)  # default to 30 if not set
            if 'Gender' not in df.columns:
                df['Gender'] = getattr(patient.user, 'gender', 'M')  # default to 'M' if not set
            if 'Weight (kg)' not in df.columns:
                df['Weight (kg)'] = getattr(patient, 'weight', 70)  # default to 70 if not set
            if 'Height (m)' not in df.columns:
                df['Height (m)'] = getattr(patient, 'height', 1.7)  # default to 1.7 if not set
            
            # Calculate derived features if not present
            if 'Derived_MAP' not in df.columns:
                df['Derived_MAP'] = (df['Systolic Blood Pressure'] + 2 * df['Diastolic Blood Pressure']) / 3
            if 'Derived_Pulse_Pressure' not in df.columns:
                df['Derived_Pulse_Pressure'] = df['Systolic Blood Pressure'] - df['Diastolic Blood Pressure']
            if 'Derived_BMI' not in df.columns:
                df['Derived_BMI'] = df['Weight (kg)'] / (df['Height (m)'] ** 2)
            if 'Derived_HRV' not in df.columns:
                df['Derived_HRV'] = df['Heart Rate'].rolling(window=5).std().fillna(0)
            
            print("Features prepared for prediction")
            print(f"Final columns: {df.columns.tolist()}")
            
            try:
                X = df[required_features]
                predictions = model.predict(X)
                df['Risk Category'] = predictions
                print(f"Made predictions: {pd.Series(predictions).value_counts().to_dict()}")
            except Exception as pred_error:
                print(f"Error making predictions: {str(pred_error)}")
                raise
        
        # Initialize alert tracking
        last_alert_time = None
        anomaly_count = 0
        ALERT_THRESHOLD = 3
        
        # Process each row
        for i in range(len(df)):
            timestamp = start_time + timedelta(seconds=i)
            is_high_risk = df.iloc[i]['Risk Category'] == 'High Risk'  # Adjust if your categories are different
            
            if is_high_risk:
                anomaly_count += 1
                print(f"Found high risk at row {i}, count: {anomaly_count}")
                
                should_create_alert = (
                    anomaly_count >= ALERT_THRESHOLD and
                    (not last_alert_time or (timestamp - last_alert_time).seconds > 100)
                )
                
                if should_create_alert:
                    vital_signs = {
                        'Heart Rate': float(df.iloc[i]['Heart Rate']),
                        'Respiratory Rate': float(df.iloc[i]['Respiratory Rate']),
                        'Body Temperature': float(df.iloc[i]['Body Temperature']),
                        'Oxygen Saturation': float(df.iloc[i]['Oxygen Saturation']),
                        'Systolic BP': float(df.iloc[i]['Systolic Blood Pressure']),
                        'Diastolic BP': float(df.iloc[i]['Diastolic Blood Pressure']),
                        'MAP': float(df.iloc[i]['Derived_MAP'])
                    }
                    
                    # Determine urgency based on consecutive high-risk readings
                    if anomaly_count >= 10:
                        urgency = 'critical'
                    elif anomaly_count >= 7:
                        urgency = 'high'
                    elif anomaly_count >= 5:
                        urgency = 'medium'
                    else:
                        urgency = 'low'
                    
                    message_parts = [f"{key}: {value:.1f}" for key, value in vital_signs.items()]
                    message = "High-risk vital signs detected:\n" + "\n".join(message_parts)
                    
                    print(f"Creating alerts for {len(doctors)} doctors at {timestamp}")
                    
                    for doctor in doctors:
                        Alert.objects.create(
                            patient=patient,
                            doctor=doctor,
                            issue=issue,
                            timestamp=current_time,
                            alert_time=timestamp,
                            urgency=urgency,
                            title=f"High-Risk Vital Signs - {patient.user.get_full_name()}",
                            message=message,
                            vital_signs_data=vital_signs
                        )
                    
                    last_alert_time = timestamp
                    print(f"Created alert with urgency: {urgency}")
            else:
                anomaly_count = 0
        
        print(f"Finished processing file for issue {issue_id}")
        return True
        
    except Exception as e:
        print(f"Error processing vital signs data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def reprocess_vital_signs_files():
    """Reprocess all existing vital signs files to generate alerts"""
    issues = Issue.objects.filter(device_data__isnull=False).exclude(device_data='')
    print(f"Found {issues.count()} issues with vital signs data to process")
    
    for issue in issues:
        file_path = os.path.join(settings.MEDIA_ROOT, issue.device_data)
        if os.path.exists(file_path):
            print(f"Processing file for issue {issue.id}: {file_path}")
            process_vital_signs_data(issue.id, file_path)
        else:
            print(f"File not found for issue {issue.id}: {file_path}") 