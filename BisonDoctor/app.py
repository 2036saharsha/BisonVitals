import asyncio
import base64
import os
import time
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

load_dotenv()

# Get Gemini API key from environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")


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

    def copy(self) -> "GeminiHandler":
        return GeminiHandler()

    async def start_up(self):
        client = genai.Client(
            api_key=GEMINI_API_KEY, http_options={"api_version": "v1alpha"}
        )
        config = {"response_modalities": ["AUDIO"]}
        async with client.aio.live.connect(
            model="gemini-2.0-flash-exp", config=config
        ) as session:
            self.session = session
            print("set session")
            while not self.quit.is_set():
                turn = self.session.receive()
                async for response in turn:
                    if data := response.data:
                        audio = np.frombuffer(data, dtype=np.int16).reshape(1, -1)
                        self.audio_queue.put_nowait(audio)

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
        "title": "Gemini Audio Video Chat",
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
    --border-radius: 15px;
    --transition: all 0.3s ease;
}

/* Base Container */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    background: var(--background-light);
    min-height: 100vh;
}

/* Header Section */
.header {
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
    color: var(--text-light);
    padding: 50px 0;
    border-radius: var(--border-radius);
    margin-bottom: 40px;
    box-shadow: var(--shadow-md);
}

.header-content {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 40px;
    padding: 0 60px;
}

.header-image {
    background: var(--card-background);
    padding: 25px;
    border-radius: 50%;
    box-shadow: var(--shadow-md);
    transition: var(--transition);
}

.header-image:hover {
    transform: scale(1.05);
}

.header-image img {
    width: 120px;
    height: 120px;
    object-fit: contain;
}

.header-text {
    text-align: left;
    max-width: 600px;
}

.header-text h1 {
    font-size: 3em;
    margin: 0;
    font-weight: 800;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    color: var(--text-light);
    letter-spacing: -0.5px;
}

.header-text p {
    font-size: 1.3em;
    margin: 15px 0;
    opacity: 0.95;
    line-height: 1.5;
    color: var(--text-light);
}

/* Main Content Sections */
.chat-container, .video-section, .image-section {
    background: var(--card-background);
    border-radius: var(--border-radius);
    padding: 40px;
    box-shadow: var(--shadow-sm);
    margin-bottom: 40px;
    border: 1px solid rgba(0, 0, 0, 0.1);
    transition: var(--transition);
}

.chat-container:hover, .video-section:hover, .image-section:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
}

/* Features Grid */
.features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 30px;
    margin: 40px 0;
}

.feature-card {
    background: var(--card-background);
    padding: 30px;
    border-radius: var(--border-radius);
    text-align: center;
    transition: var(--transition);
    border: 1px solid rgba(0, 0, 0, 0.1);
    box-shadow: var(--shadow-sm);
}

.feature-card:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-md);
    border-color: var(--primary-color);
}

.feature-icon {
    font-size: 2.5em;
    margin-bottom: 15px;
    color: var(--primary-color);
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
    text-align: center;
    padding: 40px 20px;
    background: var(--background-light);
    border-radius: var(--border-radius);
    margin-top: 40px;
    border: 1px solid rgba(0, 0, 0, 0.1);
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
    max-width: 600px;
    margin: 0 auto;
}

/* Media Container */
.media-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
    margin: 40px 0;
    align-items: start;
}

.video-section h2, .image-section h2 {
    color: var(--primary-color);
    font-size: 1.5em;
    margin-bottom: 20px;
    font-weight: 700;
    text-align: center;
}

.video-section p, .image-section p {
    color: var(--text-dark);
    font-size: 1.1em;
    line-height: 1.5;
    margin-bottom: 20px;
    text-align: center;
}

/* Video Source Styling */
#video-source {
    max-width: 800px !important;
    max-height: 600px !important;
    border-radius: var(--border-radius) !important;
    box-shadow: var(--shadow-md) !important;
    border: 2px solid var(--card-background) !important;
    background: var(--card-background) !important;
}

/* Gradio Component Styling */
.gradio-container {
    background: var(--card-background) !important;
    border-radius: var(--border-radius) !important;
    box-shadow: var(--shadow-sm) !important;
    border: 1px solid rgba(0, 0, 0, 0.1) !important;
}

.gradio-button {
    background: var(--primary-color) !important;
    color: var(--text-light) !important;
    border-radius: var(--border-radius) !important;
    transition: var(--transition) !important;
}

.gradio-button:hover {
    background: var(--primary-light) !important;
    transform: translateY(-2px);
}

/* Responsive Design */
@media (max-width: 768px) {
    .header-content {
        flex-direction: column;
        text-align: center;
        padding: 0 20px;
    }
    
    .header-text {
        text-align: center;
    }
    
    .header-text h1 {
        font-size: 2.5em;
    }
    
    .features-grid {
        grid-template-columns: 1fr;
    }
    
    .media-container {
        grid-template-columns: 1fr;
    }
    
    .video-section, .image-section {
        margin-bottom: 20px;
    }
    
    .chat-container, .video-section, .image-section {
        padding: 20px;
    }
}
"""

with gr.Blocks(css=css) as demo:
    gr.HTML(
        """
    <div class="container">
        <div class="header">
            <div class="header-content">
                <div class="header-image">
                    <img src="https://www.gstatic.com/lamda/images/gemini_favicon_f069958c85030456e93de685481c559f160ea06b.png" alt="Bison Doctor Logo">
                </div>
                <div class="header-text">
                    <h1>Bison Doctor</h1>
                    <p>Your AI-Powered Medical Assistant</p>
                    <p>Real-time video consultation with advanced AI diagnostics</p>
                </div>
            </div>
        </div>
        
        <div class="chat-container">
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
            
            <div class="consultation-section">
                <h2>Start Your Consultation</h2>
                <p>Click the video button below to begin your AI-powered medical consultation. Our advanced AI will analyze your symptoms and provide personalized medical advice.</p>
            </div>

            <div class="media-container">
                <div class="video-section">
                    <h2>Video Consultation</h2>
                    <p>Start a face-to-face consultation with our AI doctor</p>
                </div>
                <div class="image-section">
                    <h2>Medical Images</h2>
                    <p>Upload medical images for AI analysis</p>
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
                sources=["upload", "clipboard"]
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