#!/bin/bash

# Make this script executable with: chmod +x launch_visualization.sh

echo "Launching BisonBytes Vital Signs Visualization"
echo "=============================================="

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Virtual environment not found. Creating a new one..."
    python -m venv venv
    source venv/bin/activate
    
    echo "Installing required packages..."
    pip install -r requirements.txt
fi

# Launch the Streamlit app
echo "Starting Streamlit server..."
streamlit run vital_signs_streamlit.py 