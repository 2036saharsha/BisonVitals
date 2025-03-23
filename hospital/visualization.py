import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from pathlib import Path
from datetime import datetime

def load_vital_signs_data(file_path, start_time=None, end_time=None):
    """Load vital signs data from a CSV file with optional time filtering"""
    try:
        data = pd.read_csv(file_path)
        
        # Convert timestamp to datetime for filtering
        data['Timestamp'] = pd.to_datetime(data['Timestamp'])
        
        # Apply time filtering if provided
        if start_time and end_time:
            start_dt = pd.to_datetime(start_time)
            end_dt = pd.to_datetime(end_time)
            data = data[(data['Timestamp'] >= start_dt) & (data['Timestamp'] <= end_dt)]
        
        return data
    except Exception as e:
        print(f"Error loading vital signs data: {e}")
        return None

def create_timeseries_plot(data, patient_id=None):
    """Create an interactive time series plot of vital signs"""
    if patient_id:
        data = data[data['Patient ID'] == patient_id].copy()
    
    if data.empty:
        return None
    
    # Data should already have timestamps as datetime from load_vital_signs_data
    data = data.sort_values('Timestamp')
    
    # Create a subplot with 4 rows
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "Heart Rate & Respiratory Rate", 
            "Blood Pressure", 
            "Body Temperature", 
            "Oxygen Saturation"
        )
    )
    
    # Add heart rate trace
    fig.add_trace(
        go.Scatter(
            x=data['Timestamp'], 
            y=data['Heart Rate'],
            mode='lines+markers',
            name='Heart Rate',
            line=dict(color='rgba(220, 20, 60, 0.8)', width=2),
            marker=dict(size=6, color='rgba(220, 20, 60, 1.0)')
        ),
        row=1, col=1
    )
    
    # Add respiratory rate trace
    fig.add_trace(
        go.Scatter(
            x=data['Timestamp'], 
            y=data['Respiratory Rate'],
            mode='lines+markers',
            name='Respiratory Rate',
            line=dict(color='rgba(30, 144, 255, 0.8)', width=2, dash='dot'),
            marker=dict(size=6, color='rgba(30, 144, 255, 1.0)')
        ),
        row=1, col=1
    )
    
    # Add systolic blood pressure trace
    fig.add_trace(
        go.Scatter(
            x=data['Timestamp'], 
            y=data['Systolic Blood Pressure'],
            mode='lines+markers',
            name='Systolic BP',
            line=dict(color='rgba(178, 34, 34, 0.8)', width=2),
            marker=dict(size=6, color='rgba(178, 34, 34, 1.0)')
        ),
        row=2, col=1
    )
    
    # Add diastolic blood pressure trace
    fig.add_trace(
        go.Scatter(
            x=data['Timestamp'], 
            y=data['Diastolic Blood Pressure'],
            mode='lines+markers',
            name='Diastolic BP',
            line=dict(color='rgba(255, 140, 0, 0.8)', width=2),
            marker=dict(size=6, color='rgba(255, 140, 0, 1.0)')
        ),
        row=2, col=1
    )
    
    # Add body temperature trace
    fig.add_trace(
        go.Scatter(
            x=data['Timestamp'], 
            y=data['Body Temperature'],
            mode='lines+markers',
            name='Body Temperature',
            line=dict(color='rgba(75, 0, 130, 0.8)', width=2),
            marker=dict(size=6, color='rgba(75, 0, 130, 1.0)')
        ),
        row=3, col=1
    )
    
    # Add reference range for temperature
    fig.add_trace(
        go.Scatter(
            x=[data['Timestamp'].min(), data['Timestamp'].max()],
            y=[37.0, 37.0],
            mode='lines',
            name='Normal Temp',
            line=dict(color='rgba(75, 0, 130, 0.3)', width=1, dash='dash'),
            showlegend=False
        ),
        row=3, col=1
    )
    
    # Add oxygen saturation trace
    fig.add_trace(
        go.Scatter(
            x=data['Timestamp'], 
            y=data['Oxygen Saturation'],
            mode='lines+markers',
            name='Oxygen Saturation',
            line=dict(color='rgba(60, 179, 113, 0.8)', width=2),
            marker=dict(size=6, color='rgba(60, 179, 113, 1.0)')
        ),
        row=4, col=1
    )
    
    # Add reference line for oxygen saturation
    fig.add_trace(
        go.Scatter(
            x=[data['Timestamp'].min(), data['Timestamp'].max()],
            y=[95, 95],
            mode='lines',
            name='Min SpO2',
            line=dict(color='rgba(60, 179, 113, 0.3)', width=1, dash='dash'),
            showlegend=False
        ),
        row=4, col=1
    )
    
    # Update layout
    fig.update_layout(
        height=800,
        title_text=f"Patient Vital Signs Monitoring" + (f" - Patient #{patient_id}" if patient_id else ""),
        title_font=dict(size=24),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        template="plotly_white",
        margin=dict(l=60, r=40, t=80, b=40),
    )
    
    # Make plots more interactive with zoom tools
    fig.update_layout(
        xaxis=dict(
            rangeslider=dict(visible=True),
            type="date"
        )
    )
    
    # Update y-axis titles
    fig.update_yaxes(title_text="bpm", row=1, col=1)
    fig.update_yaxes(title_text="mmHg", row=2, col=1)
    fig.update_yaxes(title_text="°C", row=3, col=1)
    fig.update_yaxes(title_text="%", row=4, col=1)
    
    # Update x-axis title
    fig.update_xaxes(title_text="Timestamp", row=4, col=1)
    
    return fig

def create_correlation_heatmap(data):
    """Create a correlation heatmap of vital signs data"""
    # Select numeric columns
    numeric_cols = [
        'Heart Rate', 'Respiratory Rate', 'Body Temperature', 
        'Oxygen Saturation', 'Systolic Blood Pressure', 
        'Diastolic Blood Pressure', 'Age', 'Weight (kg)', 
        'Height (m)', 'Derived_HRV', 'Derived_Pulse_Pressure', 
        'Derived_BMI', 'Derived_MAP'
    ]
    
    # Calculate correlation matrix
    corr = data[numeric_cols].corr()
    
    # Create heatmap
    fig = px.imshow(
        corr,
        text_auto='.2f',
        color_continuous_scale='Viridis',
        title='Correlation Between Vital Signs'
    )
    
    fig.update_layout(
        height=700,
        width=900,
        title_font=dict(size=22),
        coloraxis_colorbar=dict(title="Correlation"),
    )
    
    return fig

def create_radar_chart(data, patient_id):
    """Create a radar chart showing the patient's vital signs compared to normal ranges"""
    patient_data = data[data['Patient ID'] == patient_id].iloc[0]
    
    # Define normal ranges
    normal_ranges = {
        'Heart Rate': (60, 100),
        'Respiratory Rate': (12, 20),
        'Body Temperature': (36.5, 37.5),
        'Oxygen Saturation': (95, 100),
        'Systolic Blood Pressure': (90, 120),
        'Diastolic Blood Pressure': (60, 80)
    }
    
    # Calculate normalized values (0-1 scale)
    normalized_values = {}
    for metric, (min_val, max_val) in normal_ranges.items():
        value = patient_data[metric]
        # Clip at min and max range for visualization purposes
        if value < min_val:
            normalized = 0
        elif value > max_val:
            normalized = 1
        else:
            normalized = (value - min_val) / (max_val - min_val)
        normalized_values[metric] = normalized
    
    # Create radar chart
    categories = list(normal_ranges.keys())
    
    fig = go.Figure()
    
    # Add normal range area (0.5 represents middle of normal range)
    fig.add_trace(go.Scatterpolar(
        r=[0.5] * len(categories),
        theta=categories,
        fill='toself',
        name='Normal Range',
        fillcolor='rgba(0, 128, 0, 0.2)',
        line=dict(color='green')
    ))
    
    # Add patient data
    fig.add_trace(go.Scatterpolar(
        r=[normalized_values[cat] for cat in categories],
        theta=categories,
        fill='toself',
        name=f'Patient #{patient_id}',
        fillcolor='rgba(255, 0, 0, 0.2)',
        line=dict(color='red')
    ))
    
    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        title=f"Vital Signs Profile - Patient #{patient_id}",
        title_font=dict(size=22),
        showlegend=True,
        height=600,
        width=800,
    )
    
    return fig

def create_gauge_charts(data, patient_id):
    """Create gauge charts for key vital signs"""
    # For time-filtered data, use average values
    patient_data = data[data['Patient ID'] == patient_id].mean()
    
    # Create a subplot with 6 gauge charts
    fig = make_subplots(
        rows=2, cols=3,
        specs=[[{'type': 'indicator'}, {'type': 'indicator'}, {'type': 'indicator'}],
               [{'type': 'indicator'}, {'type': 'indicator'}, {'type': 'indicator'}]],
        subplot_titles=(
            "Heart Rate (bpm)", "Respiratory Rate (breaths/min)", 
            "Body Temperature (°C)", "Oxygen Saturation (%)", 
            "Systolic BP (mmHg)", "Diastolic BP (mmHg)"
        )
    )
    
    # Heart Rate
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=patient_data['Heart Rate'],
            delta={'reference': 80},
            gauge={
                'axis': {'range': [40, 160]},
                'bar': {'color': "darkred"},
                'steps': [
                    {'range': [40, 60], 'color': "lightblue"},
                    {'range': [60, 100], 'color': "lightgreen"},
                    {'range': [100, 160], 'color': "salmon"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 120
                }
            }
        ),
        row=1, col=1
    )
    
    # Respiratory Rate
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=patient_data['Respiratory Rate'],
            delta={'reference': 16},
            gauge={
                'axis': {'range': [8, 32]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [8, 12], 'color': "lightblue"},
                    {'range': [12, 20], 'color': "lightgreen"},
                    {'range': [20, 32], 'color': "salmon"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 24
                }
            }
        ),
        row=1, col=2
    )
    
    # Body Temperature
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=patient_data['Body Temperature'],
            delta={'reference': 37.0},
            gauge={
                'axis': {'range': [35, 40]},
                'bar': {'color': "purple"},
                'steps': [
                    {'range': [35, 36], 'color': "lightblue"},
                    {'range': [36, 37.5], 'color': "lightgreen"},
                    {'range': [37.5, 40], 'color': "salmon"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 38.5
                }
            }
        ),
        row=1, col=3
    )
    
    # Oxygen Saturation
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=patient_data['Oxygen Saturation'],
            delta={'reference': 97},
            gauge={
                'axis': {'range': [80, 100]},
                'bar': {'color': "green"},
                'steps': [
                    {'range': [80, 90], 'color': "salmon"},
                    {'range': [90, 95], 'color': "lightyellow"},
                    {'range': [95, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ),
        row=2, col=1
    )
    
    # Systolic BP
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=patient_data['Systolic Blood Pressure'],
            delta={'reference': 120},
            gauge={
                'axis': {'range': [80, 200]},
                'bar': {'color': "firebrick"},
                'steps': [
                    {'range': [80, 90], 'color': "lightblue"},
                    {'range': [90, 120], 'color': "lightgreen"},
                    {'range': [120, 140], 'color': "lightyellow"},
                    {'range': [140, 200], 'color': "salmon"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 140
                }
            }
        ),
        row=2, col=2
    )
    
    # Diastolic BP
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=patient_data['Diastolic Blood Pressure'],
            delta={'reference': 80},
            gauge={
                'axis': {'range': [40, 120]},
                'bar': {'color': "orange"},
                'steps': [
                    {'range': [40, 60], 'color': "lightblue"},
                    {'range': [60, 80], 'color': "lightgreen"},
                    {'range': [80, 90], 'color': "lightyellow"},
                    {'range': [90, 120], 'color': "salmon"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ),
        row=2, col=3
    )
    
    # Calculate time period for title
    time_period = ""
    if len(data[data['Patient ID'] == patient_id]) > 1:
        min_time = data[data['Patient ID'] == patient_id]['Timestamp'].min()
        max_time = data[data['Patient ID'] == patient_id]['Timestamp'].max()
        time_period = f" (Average: {min_time.strftime('%b %d')} - {max_time.strftime('%b %d, %Y')})"
    
    # Update layout
    fig.update_layout(
        height=600,
        width=1200,
        title_text=f"Vital Signs Dashboard - Patient #{patient_id}{time_period}",
        title_font=dict(size=24),
        margin=dict(l=40, r=40, t=100, b=40)
    )
    
    return fig

def create_distribution_plots(data):
    """Create distribution plots for vital signs"""
    # Create a subplot with 6 histogram plots
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            "Heart Rate Distribution", "Respiratory Rate Distribution", 
            "Body Temperature Distribution", "Oxygen Saturation Distribution", 
            "Systolic BP Distribution", "Diastolic BP Distribution"
        )
    )
    
    # Heart Rate
    fig.add_trace(
        go.Histogram(
            x=data['Heart Rate'],
            marker_color='rgba(220, 20, 60, 0.7)',
            nbinsx=30,
            name='Heart Rate'
        ),
        row=1, col=1
    )
    
    # Respiratory Rate
    fig.add_trace(
        go.Histogram(
            x=data['Respiratory Rate'],
            marker_color='rgba(30, 144, 255, 0.7)',
            nbinsx=20,
            name='Respiratory Rate'
        ),
        row=1, col=2
    )
    
    # Body Temperature
    fig.add_trace(
        go.Histogram(
            x=data['Body Temperature'],
            marker_color='rgba(75, 0, 130, 0.7)',
            nbinsx=25,
            name='Body Temperature'
        ),
        row=2, col=1
    )
    
    # Oxygen Saturation
    fig.add_trace(
        go.Histogram(
            x=data['Oxygen Saturation'],
            marker_color='rgba(60, 179, 113, 0.7)',
            nbinsx=20,
            name='Oxygen Saturation'
        ),
        row=2, col=2
    )
    
    # Systolic BP
    fig.add_trace(
        go.Histogram(
            x=data['Systolic Blood Pressure'],
            marker_color='rgba(178, 34, 34, 0.7)',
            nbinsx=30,
            name='Systolic BP'
        ),
        row=3, col=1
    )
    
    # Diastolic BP
    fig.add_trace(
        go.Histogram(
            x=data['Diastolic Blood Pressure'],
            marker_color='rgba(255, 140, 0, 0.7)',
            nbinsx=30,
            name='Diastolic BP'
        ),
        row=3, col=2
    )
    
    # Update layout
    fig.update_layout(
        height=900,
        width=1000,
        title_text="Population Distribution of Vital Signs",
        title_font=dict(size=24),
        showlegend=False,
        template="plotly_white",
        margin=dict(l=60, r=40, t=100, b=40),
    )
    
    # Update y-axis titles
    for i in range(1, 4):
        for j in range(1, 3):
            fig.update_yaxes(title_text="Count", row=i, col=j)
    
    # Update x-axis titles
    fig.update_xaxes(title_text="bpm", row=1, col=1)
    fig.update_xaxes(title_text="breaths/min", row=1, col=2)
    fig.update_xaxes(title_text="°C", row=2, col=1)
    fig.update_xaxes(title_text="%", row=2, col=2)
    fig.update_xaxes(title_text="mmHg", row=3, col=1)
    fig.update_xaxes(title_text="mmHg", row=3, col=2)
    
    return fig

def create_risk_analysis_charts(data):
    """Create charts analyzing the relationship between vital signs and risk categories"""
    # Count risk categories
    risk_counts = data['Risk Category'].value_counts().reset_index()
    risk_counts.columns = ['Risk Category', 'Count']
    
    # Create subplot with 2 charts
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        subplot_titles=("Risk Category Distribution", "Average Vital Signs by Risk Category")
    )
    
    # Add pie chart for risk distribution
    fig.add_trace(
        go.Pie(
            labels=risk_counts['Risk Category'],
            values=risk_counts['Count'],
            hole=0.4,
            marker=dict(
                colors=['rgba(255, 0, 0, 0.7)', 'rgba(255, 165, 0, 0.7)', 'rgba(0, 128, 0, 0.7)']
            ),
            textinfo='label+percent',
            textposition='outside',
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Calculate average vital signs by risk category
    risk_avg = data.groupby('Risk Category')[
        ['Heart Rate', 'Respiratory Rate', 'Body Temperature', 
         'Oxygen Saturation', 'Systolic Blood Pressure', 'Diastolic Blood Pressure']
    ].mean().reset_index()
    
    # Normalize the data for better visualization
    # Get min and max values for each vital sign
    min_vals = data[['Heart Rate', 'Respiratory Rate', 'Body Temperature', 
                     'Oxygen Saturation', 'Systolic Blood Pressure', 'Diastolic Blood Pressure']].min()
    max_vals = data[['Heart Rate', 'Respiratory Rate', 'Body Temperature', 
                     'Oxygen Saturation', 'Systolic Blood Pressure', 'Diastolic Blood Pressure']].max()
    
    # Normalize the values
    for col in ['Heart Rate', 'Respiratory Rate', 'Body Temperature', 
                'Oxygen Saturation', 'Systolic Blood Pressure', 'Diastolic Blood Pressure']:
        risk_avg[f'{col}_norm'] = (risk_avg[col] - min_vals[col]) / (max_vals[col] - min_vals[col])
    
    # Add grouped bar chart for vital signs by risk
    for i, risk in enumerate(risk_avg['Risk Category']):
        fig.add_trace(
            go.Bar(
                x=['HR', 'RR', 'Temp', 'SpO2', 'SBP', 'DBP'],
                y=[
                    risk_avg.loc[i, 'Heart Rate_norm'],
                    risk_avg.loc[i, 'Respiratory Rate_norm'],
                    risk_avg.loc[i, 'Body Temperature_norm'],
                    risk_avg.loc[i, 'Oxygen Saturation_norm'],
                    risk_avg.loc[i, 'Systolic Blood Pressure_norm'],
                    risk_avg.loc[i, 'Diastolic Blood Pressure_norm']
                ],
                name=risk,
                marker_color=['red', 'orange', 'green'][i % 3]  # Use modulo in case there are more than 3 categories
            ),
            row=1, col=2
        )
    
    # Update layout
    fig.update_layout(
        height=500,
        width=1100,
        title_text="Risk Analysis Based on Vital Signs",
        title_font=dict(size=22),
        barmode='group',
        margin=dict(l=40, r=40, t=80, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(title_text="Vital Sign", row=1, col=2)
    fig.update_yaxes(title_text="Normalized Value", row=1, col=2)
    
    return fig

def generate_vital_signs_plots(file_path, patient_id=None, start_time=None, end_time=None):
    """Generate all plots for a patient's vital signs data with optional time filtering"""
    data = load_vital_signs_data(file_path, start_time, end_time)
    
    if data is None:
        return None
    
    plots = {}
    timestamps = []
    
    # Extract timestamps for the time range slider
    if patient_id:
        patient_data = data[data['Patient ID'] == int(patient_id)]
        if not patient_data.empty:
            # Get unique timestamps for this patient and convert to ISO format strings
            timestamps = patient_data['Timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ').tolist()
    
    # If patient_id is specified, create patient-specific visualizations
    if patient_id:
        # Make sure patient_id is numeric
        patient_id = int(patient_id)
        
        # Check if patient exists in data
        if patient_id not in data['Patient ID'].values:
            return None
        
        # Generate patient-specific plots
        plots['timeseries'] = create_timeseries_plot(data, patient_id)
        plots['radar'] = create_radar_chart(data, patient_id)
        plots['gauges'] = create_gauge_charts(data, patient_id)
    
    # Generate population-level plots
    plots['distribution'] = create_distribution_plots(data)
    plots['correlation'] = create_correlation_heatmap(data)
    plots['risk_analysis'] = create_risk_analysis_charts(data)
    
    # Convert plots to JSON
    plot_jsons = {}
    for key, fig in plots.items():
        if fig is not None:
            plot_jsons[key] = fig.to_json()
    
    # Add timestamps to the response
    if timestamps:
        plot_jsons['timestamps'] = timestamps
    
    return plot_jsons 