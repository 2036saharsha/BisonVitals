# Bison Doctor: AI-Powered Medical Assistant

![Bison Doctor Logo](https://www.shutterstock.com/image-vector/male-doctor-smiling-happy-face-600nw-2481032615.jpg)

## Overview

Bison Doctor is an AI-powered medical assistant designed to facilitate professional medical consultations through audio and video interactions. Leveraging advanced AI technology, Bison Doctor provides preliminary medical advice, gathers relevant medical history, and offers lifestyle recommendations while maintaining a compassionate and professional demeanor.

## Features

- **Audio and Video Consultations**: Conduct real-time consultations with an AI doctor.
- **AI Diagnostics**: Get advanced medical analysis and insights powered by AI.
- **User-Friendly Interface**: Intuitive design for easy navigation and interaction.
- **Secure and Private**: Your health data is protected with enterprise-grade security.
- **Emergency Call Functionality**: Quickly connect to emergency services with a single click.

## Technologies Used

- **Gradio**: For building the user interface.
- **WebRTC**: For real-time audio and video communication.
- **Google GenAI**: For AI-powered medical responses.
- **Python**: The primary programming language for backend development.
- **PIL**: For image processing.

## Installation

To set up the Bison Doctor project locally, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/2036saharsha/BisonVitals.git
   cd BisonVitals
   ```

2. **Create a Virtual Environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**:
   Create a `.env` file in the root directory and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

5. **Run the Application**:
   ```bash
   python app.py
   ```

6. **Access the Application**:
   Open your web browser and navigate to `http://localhost:7860`.

## Usage

- **Start a Consultation**: Click on the "Start Your Consultation" button to begin.
- **Upload Medical Images**: Use the upload feature to share relevant medical images.
- **Emergency Call**: Click the "Emergency Call" button to connect with emergency services.

## Contributing

We welcome contributions to improve Bison Doctor! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push your changes to your forked repository.
5. Create a pull request detailing your changes.

Thank you for using Bison Doctor! We hope it enhances your medical consultation experience.