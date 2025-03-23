import os
import sys
import subprocess
import venv
from pathlib import Path

def main():
    """Launch the Streamlit visualization app"""
    print("Launching BisonBytes Vital Signs Visualization")
    print("==============================================")
    
    # Determine the root directory
    root_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    venv_dir = root_dir / "venv"
    requirements_file = root_dir / "requirements.txt"
    
    # Check if virtual environment exists
    if not venv_dir.exists():
        print("Virtual environment not found. Creating a new one...")
        venv.create(venv_dir, with_pip=True)
        
        # Path to pip in the virtual environment
        if sys.platform == 'win32':
            pip_path = venv_dir / "Scripts" / "pip.exe"
        else:
            pip_path = venv_dir / "bin" / "pip"
        
        # Install requirements
        print("Installing required packages...")
        subprocess.run([str(pip_path), "install", "-r", str(requirements_file)])
    
    # Path to streamlit in the virtual environment
    if sys.platform == 'win32':
        streamlit_path = venv_dir / "Scripts" / "streamlit.exe"
    else:
        streamlit_path = venv_dir / "bin" / "streamlit"
    
    # Launch the Streamlit app
    print("Starting Streamlit server...")
    streamlit_script = root_dir / "vital_signs_streamlit.py"
    subprocess.run([str(streamlit_path), "run", str(streamlit_script)])

if __name__ == "__main__":
    main() 