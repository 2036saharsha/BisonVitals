import asyncio
import base64
import os
import time
import logging
from io import BytesIO

import gradio as gr
from gradio.utils import get_space
import numpy as np
from google import genai
from dotenv import load_dotenv
from fastrtc import (
    AsyncAudioVideoStreamHandler,
    Stream,
    get_twilio_turn_credentials,
    WebRTC,
)
from PIL import Image

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audio_conversation.log'),
        logging.StreamHandler()
    ]
)

load_dotenv()

# Get Gemini API key from environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

# System prompt for audio interactions
AUDIO_SYSTEM_PROMPT = """You are Bison Doctor, an AI-powered medical assistant. Your role is to:

1. Conduct professional medical consultations through audio interaction
2. Provide preliminary medical advice and recommendations
3. Maintain a compassionate and professional demeanor
4. Always emphasize that you are an AI assistant and not a replacement for professional medical care
5. For serious conditions, always recommend consulting a healthcare professional
6. Focus on:
   - Gathering relevant medical history
   - Understanding current symptoms
   - Providing general health advice
   - Suggesting lifestyle modifications
   - Recommending when to seek professional medical attention

Important Guidelines:
- Never prescribe medications
- Never diagnose serious conditions
- Always maintain patient privacy and confidentiality
- Be clear about your limitations as an AI
- Encourage professional medical consultation for serious concerns
- Provide information in a clear, understandable manner
- Use appropriate medical terminology while explaining in layman's terms
- Maintain a supportive and empathetic tone
- Keep responses concise and focused
- Speak clearly and at a natural pace
- Use appropriate pauses between sentences
- Maintain a professional but friendly tone

Remember: Your role is to assist and inform, not to replace professional medical care."""

def encode_audio(data: np.ndarray) -> dict:
    """Encode Audio data to send to the server"""
    return {
        "mime_type": "audio/pcm",
        "data": base64.b64encode(data.tobytes()).decode("UTF-8"),
    }


def encode_image(data: np.ndarray) -> dict:
    with BytesIO() as output_bytes:
        pil_image = Image.fromarray(data)
        pil_image.save(output_bytes, "JPEG")
        bytes_data = output_bytes.getvalue()
    base64_str = str(base64.b64encode(bytes_data), "utf-8")
    return {"mime_type": "image/jpeg", "data": base64_str}


class GeminiHandler(AsyncAudioVideoStreamHandler):
    def __init__(
        self,
    ) -> None:
        super().__init__(
            "mono",
            output_sample_rate=24000,
            output_frame_size=480,
            input_sample_rate=16000,
        )
        self.audio_queue = asyncio.Queue()
        self.video_queue = asyncio.Queue()
        self.quit = asyncio.Event()
        self.session = None
        self.last_frame_time = 0
        self.quit = asyncio.Event()
        # Initialize conversation history
        self.conversation_history = []
        self.max_history_length = 10  # Keep last 10 interactions
        self.last_audio_send_time = 0
        self.audio_send_interval = 0.5  # Minimum time between audio sends in seconds
        logging.info("Initialized GeminiHandler with conversation history tracking")

    def copy(self) -> "GeminiHandler":
        return GeminiHandler()

    def update_conversation_history(self, user_input: str, ai_response: str):
        """Update conversation history with new interaction"""
        if not user_input and not ai_response:
            return
            
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": ai_response
        })
        # Keep only the last max_history_length interactions
        if len(self.conversation_history) > self.max_history_length * 2:
            self.conversation_history = self.conversation_history[-self.max_history_length * 2:]
        logging.info(f"Updated conversation history - User: {user_input[:50]}... AI: {ai_response[:50]}...")

    async def start_up(self):
        client = genai.Client(
            api_key=GEMINI_API_KEY, http_options={"api_version": "v1alpha"}
        )
        config = {
            "response_modalities": ["AUDIO"],
            "system_prompt": AUDIO_SYSTEM_PROMPT,
            "history": self.conversation_history  # Include conversation history in config
        }
        logging.info("Starting up GeminiHandler with audio response modality")
        try:
            async with client.aio.live.connect(
                model="gemini-2.0-flash-exp", config=config
            ) as session:
                self.session = session
                logging.info("Session established")
                while not self.quit.is_set():
                    try:
                        turn = self.session.receive()
                        async for response in turn:
                            if data := response.data:
                                audio = np.frombuffer(data, dtype=np.int16).reshape(1, -1)
                                self.audio_queue.put_nowait(audio)
                                # Update conversation history with AI response
                                if hasattr(response, 'text') and response.text:
                                    logging.info(f"Received AI response: {response.text[:100]}...")
                                    self.update_conversation_history("", response.text)
                    except websockets.exceptions.ConnectionClosedOK:
                        logging.info("WebSocket connection closed normally")
                        break
                    except Exception as e:
                        logging.error(f"Error in start_up loop: {str(e)}")
                        break
        except Exception as e:
            logging.error(f"Error in start_up: {str(e)}")
        finally:
            self.quit.set()
            if self.session:
                try:
                    await self.session._websocket.close()
                except:
                    pass
            self.quit.clear()

    async def video_receive(self, frame: np.ndarray):
        if self.session:
            # send image every 1 second
            print(time.time() - self.last_frame_time)
            if time.time() - self.last_frame_time > 1:
                self.last_frame_time = time.time()
                await self.session.send(input=encode_image(frame))
                if self.latest_args[1] is not None:
                    await self.session.send(input=encode_image(self.latest_args[1]))

        self.video_queue.put_nowait(frame)

    async def video_emit(self):
        return await self.video_queue.get()

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        _, array = frame
        array = array.squeeze()
        audio_message = encode_audio(array)
        if self.session:
            await self.session.send(input=audio_message)

    async def emit(self):
        array = await self.audio_queue.get()
        return (self.output_sample_rate, array)

    async def shutdown(self) -> None:
        if self.session:
            self.quit.set()
            await self.session._websocket.close()
            self.quit.clear()


stream = Stream(
    handler=GeminiHandler(),
    modality="audio-video",
    mode="send-receive",
    rtc_configuration=get_twilio_turn_credentials()
    if get_space()
    else None,
    time_limit=90 if get_space() else None,
    additional_inputs=[
        gr.Image(label="Image", type="numpy", sources=["upload", "clipboard"])
    ],
    ui_args={
        "icon": "https://www.gstatic.com/lamda/images/gemini_favicon_f069958c85030456e93de685481c559f160ea06b.png",
        "pulse_color": "rgb(255, 255, 255)",
        "icon_button_color": "rgb(255, 255, 255)",
        "title": "AI Doctor",
    },
)

css = """
/* Global Styles */
:root {
    --primary-color: #1a237e;
    --primary-light: #534bae;
    --primary-dark: #000051;
    --secondary-color: #0d47a1;
    --text-light: #ffffff;
    --text-dark: #4a4a4a;
    --background-light: #f0f2f5;
    --card-background: #ffffff;
    --shadow-sm: 0 4px 16px rgba(0, 0, 0, 0.08);
    --shadow-md: 0 8px 32px rgba(0, 0, 0, 0.15);
    --shadow-lg: 0 12px 48px rgba(0, 0, 0, 0.2);
    --border-radius: 15px;
    --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    --max-width: 100%;
    --component-width: 100%;
    --container-padding: 2rem;
    --gradient-primary: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
    --gradient-hover: linear-gradient(135deg, var(--primary-light) 0%, var(--secondary-color) 100%);
    --gradient-text: linear-gradient(45deg, #fff, #e3f2fd);
    --gradient-border: linear-gradient(45deg, #ff6b6b, #4ecdc4);
    --gradient-glow: linear-gradient(45deg, rgba(255,255,255,0.1), rgba(255,255,255,0.2));
}

/* Cool Animations */
@keyframes float {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
    100% { transform: translateY(0px); }
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}

@keyframes shine {
    0% { background-position: -100% 0; }
    100% { background-position: 200% 0; }
}

@keyframes rotate {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

@keyframes glow {
    0% { box-shadow: 0 0 5px rgba(255,255,255,0.5); }
    50% { box-shadow: 0 0 20px rgba(255,255,255,0.8); }
    100% { box-shadow: 0 0 5px rgba(255,255,255,0.5); }
}

/* Enhanced Header */
.header {
    background: var(--gradient-primary);
    color: var(--text-light);
    padding: 2rem 0;
    margin: 0;
    box-shadow: var(--shadow-lg);
    width: 100%;
    box-sizing: border-box;
    border-radius: 0;
    position: relative;
    overflow: hidden;
    animation: glow 3s infinite;
}

.header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--gradient-glow);
    opacity: 0.5;
    animation: shine 3s linear infinite;
}

.header-content {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 3rem;
    padding: 0 var(--container-padding);
    width: 100%;
    margin: 0 auto;
    box-sizing: border-box;
    position: relative;
    z-index: 1;
    animation: float 6s ease-in-out infinite;
}

.header-image {
    background: var(--card-background);
    padding: 20px;
    border-radius: 50%;
    box-shadow: var(--shadow-lg);
    transition: var(--transition);
    position: relative;
    overflow: hidden;
    animation: pulse 4s infinite;
    width: 200px;
    height: 200px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 3px solid rgba(255,255,255,0.2);
}

.header-image::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--gradient-primary);
    opacity: 0;
    transition: var(--transition);
    z-index: -1;
    animation: rotate 10s linear infinite;
}

.header-image:hover {
    transform: scale(1.1) rotate(10deg);
    box-shadow: var(--shadow-lg);
}

.header-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: var(--transition);
    border-radius: 50%;
    image-rendering: -webkit-optimize-contrast;
    image-rendering: crisp-edges;
}

/* Enhanced Status Indicator */
.status-indicator {
    position: absolute;
    top: 1rem;
    right: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(255, 255, 255, 0.1);
    padding: 0.5rem 1rem;
    border-radius: 20px;
    backdrop-filter: blur(5px);
    border: 1px solid rgba(255,255,255,0.2);
    animation: float 3s ease-in-out infinite;
}

.status-dot {
    width: 8px;
    height: 8px;
    background: #4CAF50;
    border-radius: 50%;
    animation: pulse 2s infinite;
    box-shadow: 0 0 10px #4CAF50;
}

.status-text {
    color: var(--text-light);
    font-size: 0.9em;
    font-weight: 500;
}

/* Enhanced Quick Actions */
.action-button {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255,255,255,0.2);
    padding: 0.5rem 1rem;
    border-radius: 20px;
    color: var(--text-light);
    cursor: pointer;
    transition: var(--transition);
    backdrop-filter: blur(5px);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    position: relative;
    overflow: hidden;
}

.action-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: 0.5s;
}

.action-button:hover {
    background: rgba(255, 255, 255, 0.2);
    transform: translateY(-2px) scale(1.05);
    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
}

.action-button:hover::before {
    left: 100%;
}

/* Enhanced Feature Cards */
.feature-card {
    background: var(--card-background);
    padding: 1.5rem;
    border-radius: var(--border-radius);
    text-align: center;
    transition: var(--transition);
    border: 1px solid rgba(0, 0, 0, 0.1);
    box-shadow: var(--shadow-sm);
    width: 100%;
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
    animation: float 6s ease-in-out infinite;
}

.feature-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: var(--gradient-primary);
    opacity: 0;
    transition: var(--transition);
    z-index: 0;
}

.feature-card:hover {
    transform: translateY(-10px) scale(1.02);
    box-shadow: var(--shadow-lg);
    border-color: transparent;
}

.feature-card:hover::before {
    opacity: 0.1;
}

.feature-icon {
    font-size: 2.5em;
    margin-bottom: 15px;
    color: var(--primary-color);
    transition: var(--transition);
    animation: pulse 3s infinite;
}

.feature-card:hover .feature-icon {
    transform: scale(1.3) rotate(10deg);
    color: var(--primary-color);
}

/* Enhanced Gradio Components */
.gradio-button {
    background: var(--gradient-primary) !important;
    color: var(--text-light) !important;
    border-radius: var(--border-radius) !important;
    transition: var(--transition) !important;
    box-sizing: border-box !important;
    padding: 1rem !important;
    margin: 0.5rem 0 !important;
    position: relative !important;
    overflow: hidden !important;
    border: none !important;
    cursor: pointer !important;
    animation: float 4s ease-in-out infinite;
}

.gradio-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: 0.5s;
}

.gradio-button:hover {
    transform: translateY(-3px) scale(1.02);
    box-shadow: var(--shadow-lg);
}

.gradio-button:hover::before {
    left: 100%;
}

/* Enhanced Image Input */
.image-input {
    border: 2px solid transparent !important;
    background: linear-gradient(var(--card-background), var(--card-background)) padding-box,
                var(--gradient-border) border-box !important;
    border-radius: var(--border-radius) !important;
    box-shadow: var(--shadow-sm) !important;
    box-sizing: border-box !important;
    transition: var(--transition) !important;
    animation: float 5s ease-in-out infinite;
}

.image-input:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-lg);
}

/* Enhanced Video Source */
#video-source {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 1rem !important;
    border-radius: var(--border-radius) !important;
    box-shadow: var(--shadow-sm) !important;
    border: 2px solid transparent !important;
    background: linear-gradient(var(--card-background), var(--card-background)) padding-box,
                var(--gradient-border) border-box !important;
    box-sizing: border-box !important;
    transition: var(--transition) !important;
}

#video-source:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-lg);
}

#video-source video {
    border-radius: var(--border-radius) !important;
    overflow: hidden !important;
}

.gradio-video {
    border-radius: var(--border-radius) !important;
    overflow: hidden !important;
}

/* Responsive Enhancements */
@media (max-width: 768px) {
    .header-content {
        animation: none;
    }
    
    .feature-card {
        animation: none;
    }
    
    .gradio-button {
        animation: none;
    }
    
    .image-input, #video-source {
        animation: none;
    }
}

/* Main Content Layout */
.main-content {
    display: flex;
    flex-direction: column;
    gap: 0;
    width: 100%;
    margin: 0;
    box-sizing: border-box;
    padding: 0;
}

/* Features Grid */
.features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
    width: 100%;
    box-sizing: border-box;
    padding: 1rem var(--container-padding);
}

.feature-card {
    background: var(--card-background);
    padding: 1.5rem;
    border-radius: var(--border-radius);
    text-align: center;
    transition: var(--transition);
    border: 1px solid rgba(0, 0, 0, 0.1);
    box-shadow: var(--shadow-sm);
    width: 100%;
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
}

.feature-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: var(--gradient-primary);
    opacity: 0;
    transition: var(--transition);
    z-index: 0;
}

.feature-card:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-lg);
    border-color: transparent;
}

.feature-card:hover::before {
    opacity: 0.05;
}

.feature-card:hover .feature-icon {
    transform: scale(1.2) rotate(5deg);
    color: var(--primary-color);
}

.feature-card:hover .feature-title {
    color: var(--primary-color);
}

.feature-card:hover .feature-description {
    color: var(--text-dark);
}

.feature-icon {
    font-size: 2.5em;
    margin-bottom: 15px;
    color: var(--primary-color);
    transition: var(--transition);
}

.feature-title {
    font-weight: 700;
    color: var(--primary-color);
    margin-bottom: 12px;
    font-size: 1.3em;
}

.feature-description {
    color: var(--text-dark);
    font-size: 1em;
    line-height: 1.5;
}

/* Consultation Section */
.consultation-section {
    background: var(--card-background);
    padding: 2rem;
    border-radius: var(--border-radius);
    text-align: center;
    box-shadow: var(--shadow-sm);
    border: 1px solid rgba(0, 0, 0, 0.1);
    width: 100%;
    box-sizing: border-box;
    transition: var(--transition);
    position: relative;
    overflow: hidden;
}

.consultation-section::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: var(--gradient-primary);
    opacity: 0;
    transition: var(--transition);
    z-index: 0;
}

.consultation-section:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-lg);
    border-color: transparent;
}

.consultation-section:hover::before {
    opacity: 0.05;
}

.consultation-section:hover h2 {
    color: var(--primary-color);
    transform: translateY(-2px);
}

.consultation-section:hover p {
    color: var(--text-dark);
    transform: translateY(-2px);
}

.consultation-section h2 {
    color: var(--primary-color);
    font-size: 2em;
    margin-bottom: 15px;
    font-weight: 700;
}

.consultation-section p {
    color: var(--text-dark);
    font-size: 1.2em;
    line-height: 1.6;
    max-width: 800px;
    margin: 0 auto;
}

/* Media Container */
.media-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    width: 100%;
    box-sizing: border-box;
}

.video-section, .image-section {
    background: var(--card-background);
    padding: 2rem;
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-sm);
    border: 1px solid rgba(0, 0, 0, 0.1);
    width: 100%;
    box-sizing: border-box;
    transition: var(--transition);
    cursor: pointer;
    position: relative;
    overflow: hidden;
}

.video-section::before, .image-section::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: var(--gradient-primary);
    opacity: 0;
    transition: var(--transition);
    z-index: 0;
}

.video-section:hover, .image-section:hover {
    transform: translateY(-5px) scale(1.02);
    box-shadow: var(--shadow-lg);
    border-color: transparent;
}

.video-section:hover::before, .image-section:hover::before {
    opacity: 0.05;
}

.video-section:hover .icon, .image-section:hover .icon {
    transform: scale(1.2) rotate(5deg);
}

.video-section:hover h2, .image-section:hover h2 {
    color: var(--primary-color);
    transform: translateY(-2px);
}

.video-section:hover p, .image-section:hover p {
    color: var(--text-dark);
    transform: translateY(-2px);
}

/* Video Source Styling */
#video-source {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    border: none !important;
    background: var(--card-background) !important;
    box-sizing: border-box !important;
}

/* Gradio Component Styling */
.gradio-container {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    box-sizing: border-box !important;
}

/* Row and Column Layout */
.gradio-row {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    box-sizing: border-box !important;
}

.gradio-column {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    box-sizing: border-box !important;
}

/* Button Styling */
.gradio-button {
    width: 100% !important;
    max-width: 100% !important;
    background: var(--gradient-primary) !important;
    color: var(--text-light) !important;
    border-radius: var(--border-radius) !important;
    transition: var(--transition) !important;
    box-sizing: border-box !important;
    padding: 1rem !important;
    margin: 0.5rem 0 !important;
    position: relative !important;
    overflow: hidden !important;
    border: none !important;
    cursor: pointer !important;
}

.gradio-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: var(--gradient-hover);
    opacity: 0;
    transition: var(--transition);
}

.gradio-button:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}

.gradio-button:hover::before {
    opacity: 1;
}

/* Image Input Styling */
.image-input {
    width: 100% !important;
    max-width: 100% !important;
    border-radius: var(--border-radius) !important;
    box-shadow: var(--shadow-sm) !important;
    border: 1px solid rgba(0, 0, 0, 0.1) !important;
    box-sizing: border-box !important;
}

/* Responsive Design */
@media (max-width: 768px) {
    :root {
        --container-padding: 1rem;
    }
    
    .header {
        margin: 0;
        width: 100%;
        padding: 1.5rem 0;
    }
    
    .features-grid {
        padding: 0.5rem var(--container-padding);
    }
    
    .feature-card {
        padding: 1rem;
    }
    
    .header-content {
        flex-direction: column;
        text-align: center;
        padding: 0 1rem;
    }
    
    .media-container {
        grid-template-columns: 1fr;
    }
    
    .features-grid {
        grid-template-columns: 1fr;
    }
    
    .gradio-row {
        flex-direction: column !important;
    }
    
    .gradio-column {
        width: 100% !important;
    }
}

/* Enhanced Header Text */
.header-text {
    text-align: left;
    max-width: 600px;
    flex: 1;
    position: relative;
    z-index: 2;
    background: rgba(0,0,0,0.1);
    padding: 2rem;
    border-radius: 15px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.1);
}

.header-text h1 {
    font-size: 4.5em;
    margin: 0;
    font-weight: 900;
    text-shadow: 
        2px 2px 0 rgba(0,0,0,0.2),
        0 0 10px rgba(255,255,255,0.8);
    color: #ffffff;
    letter-spacing: -1px;
    position: relative;
    display: inline-block;
    background: linear-gradient(45deg, #ffffff 30%, #e3f2fd 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    transform-style: preserve-3d;
    perspective: 1000px;
}

.header-text h1::before {
    content: 'Bison Doctor';
    position: absolute;
    left: 0;
    top: 0;
    z-index: -1;
    background: linear-gradient(45deg, #1a237e 30%, #0d47a1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    opacity: 0.8;
    transform: translateZ(-5px);
}

.header-text h1 span {
    display: inline-block;
    text-shadow: none;
    background: linear-gradient(45deg, #ffffff 30%, #e3f2fd 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 900;
    position: relative;
}

.header-text h1 span::after {
    content: attr(data-text);
    position: absolute;
    left: 0;
    top: 0;
    z-index: -1;
    background: linear-gradient(45deg, #1a237e 30%, #0d47a1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    opacity: 0.8;
}

@keyframes letterFloat {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-5px); }
}

@keyframes titleFloat {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-3px); }
}

.header-text p {
    font-size: 1.4em;
    margin: 15px 0;
    opacity: 1;
    line-height: 1.6;
    color: #ffffff;
    font-weight: 500;
    text-shadow: 1px 1px 0 rgba(0,0,0,0.2);
    position: relative;
    display: inline-block;
}
"""

with gr.Blocks(css=css) as demo:
    gr.HTML(
        """
    <div class="container">
        <div class="header">
            <div class="status-indicator">
                <div class="status-dot"></div>
                <span class="status-text">AI Assistant Online</span>
            </div>
            <div class="header-content">
                <div class="header-image">
                    <img src="https://www.shutterstock.com/image-vector/male-doctor-smiling-happy-face-600nw-2481032615.jpg" alt="AI Doctor">
                </div>
                <div class="header-text">
                    <h1><span>B</span><span>i</span><span>s</span><span>o</span><span>n</span> <span>D</span><span>o</span><span>c</span><span>t</span><span>o</span><span>r</span></h1>
                    <p>Your AI-Powered Medical Assistant</p>
                    <p>Real-time video consultation with advanced AI diagnostics</p>
                </div>
            </div>
            <div class="quick-actions">
                <button class="action-button" onclick="startEmergencyCall()">
                    <span>📞</span> Emergency Call
                </button>
                <button class="action-button">
                    <span>📝</span> History
                </button>
            </div>
            <!-- Emergency Call Modal -->
            <div id="emergencyModal" class="emergency-modal">
                <div class="emergency-modal-content">
                    <h2>Emergency Call</h2>
                    <p>Connecting to emergency services...</p>
                    <div class="call-controls">
                        <button id="startCall" class="call-button">Start Call</button>
                        <button id="endCall" class="call-button end-call">End Call</button>
                    </div>
                    <div class="call-status"></div>
                    <audio id="remoteAudio" autoplay></audio>
                </div>
            </div>
        </div>
        
        <style>
        .emergency-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            backdrop-filter: blur(5px);
        }
        
        .emergency-modal-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            min-width: 300px;
            box-shadow: 0 0 20px rgba(0,0,0,0.2);
        }
        
        .call-controls {
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin-top: 1rem;
        }
        
        .call-button {
            padding: 0.8rem 1.5rem;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
            background: var(--gradient-primary);
            color: white;
        }
        
        .end-call {
            background: linear-gradient(45deg, #ff4b4b, #ff6b6b);
        }
        
        .call-status {
            margin-top: 1rem;
            font-weight: 500;
            color: #666;
        }
        </style>
        
        <script>
        let pc = null;
        
        function startEmergencyCall() {
            document.getElementById('emergencyModal').style.display = 'block';
            
            document.getElementById('startCall').addEventListener('click', initializeCall);
            document.getElementById('endCall').addEventListener('click', endCall);
        }
        
        async function initializeCall() {
            try {
                // Create WebRTC peer connection
                pc = new RTCPeerConnection({
                    iceServers: [
                        { urls: 'stun:stun.l.google.com:19302' }
                    ]
                });
                
                // Get user's audio
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach(track => pc.addTrack(track, stream));
                
                // Handle incoming audio
                pc.ontrack = event => {
                    const remoteAudio = document.getElementById('remoteAudio');
                    if (remoteAudio.srcObject !== event.streams[0]) {
                        remoteAudio.srcObject = event.streams[0];
                    }
                };
                
                // Create and set local description
                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);
                
                // Update status
                document.querySelector('.call-status').textContent = 'Call Connected';
                document.getElementById('startCall').disabled = true;
                
            } catch (err) {
                console.error('Error starting call:', err);
                document.querySelector('.call-status').textContent = 'Failed to connect call';
            }
        }
        
        function endCall() {
            if (pc) {
                pc.close();
                pc = null;
            }
            document.getElementById('emergencyModal').style.display = 'none';
            document.getElementById('startCall').disabled = false;
            document.querySelector('.call-status').textContent = '';
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('emergencyModal');
            if (event.target == modal) {
                endCall();
            }
        }
        </script>
        
        <div class="main-content">
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon">🎥</div>
                    <div class="feature-title">Video Consultation</div>
                    <div class="feature-description">High-quality video calls with your AI doctor for personalized medical advice</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🤖</div>
                    <div class="feature-title">AI Diagnostics</div>
                    <div class="feature-description">Advanced AI-powered medical analysis for accurate health insights</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🔒</div>
                    <div class="feature-title">Secure & Private</div>
                    <div class="feature-description">Your health data is protected with enterprise-grade security</div>
                </div>
            </div>
        </div>
    </div>
    """
    )
    with gr.Row() as row:
        with gr.Column():
            webrtc = WebRTC(
                label="Video Consultation",
                modality="audio-video",
                mode="send-receive",
                elem_id="video-source",
                rtc_configuration=get_twilio_turn_credentials()
                if get_space()
                else None,
                icon="https://www.gstatic.com/lamda/images/gemini_favicon_f069958c85030456e93de685481c559f160ea06b.png",
                pulse_color="rgb(26, 35, 126)",
                icon_button_color="rgb(26, 35, 126)",
            )
        with gr.Column():
            image_input = gr.Image(
                label="Upload Medical Images", 
                type="numpy", 
                sources=["upload", "clipboard"],
                elem_classes="image-input"
            )

        webrtc.stream(
            GeminiHandler(),
            inputs=[webrtc, image_input],
            outputs=[webrtc],
            time_limit=60 if get_space() else None,
            concurrency_limit=2 if get_space() else None,
        )

stream.ui = demo


if __name__ == "__main__":
    if (mode := os.getenv("MODE")) == "UI":
        stream.ui.launch(server_port=7860)
    elif mode == "PHONE":
        raise ValueError("Phone mode not supported for this demo")
    else:
        stream.ui.launch(server_port=7860)