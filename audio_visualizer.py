import streamlit.components.v1 as components
import pyaudio
import numpy as np
from threading import Event
import json

class AudioVisualizer:
    def __init__(self):
        # Audio configuration
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.stop_event = Event()
        self.audio_data = np.zeros(self.CHUNK)
        
        # HTML/JS for visualization
        self.visualizer_html = """
        <canvas id="visualizer" width="400" height="100"></canvas>
        <script>
            const canvas = document.getElementById('visualizer');
            const ctx = canvas.getContext('2d');
            let audioData = [];
            
            function draw() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // Create gradient
                const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
                gradient.addColorStop(0, '#2B7A78');
                gradient.addColorStop(1, '#3AAFA9');
                ctx.fillStyle = gradient;
                
                // Draw bars
                const barCount = 50;
                const maxHeight = 100;
                
                for (let i = 0; i < barCount; i++) {
                    const index = Math.floor(i * audioData.length / barCount);
                    const height = (audioData[index] / 255) * maxHeight;
                    const barWidth = 6;
                    const spacing = 2;
                    ctx.fillRect(i * (barWidth + spacing), canvas.height - height, barWidth, height);
                }
                
                requestAnimationFrame(draw);
            }
            
            // Start animation
            draw();
        </script>
        """
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        audio_array = np.frombuffer(in_data, dtype=np.int16)
        self.audio_data = np.abs(audio_array) / 32768 * 255  # Normalize to 0-255
        return (in_data, pyaudio.paContinue)
    
    def start(self):
        try:
            self.stop_event.clear()
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                stream_callback=self.audio_callback
            )
            self.stream.start_stream()
            return True
        except Exception as e:
            print(f"Audio stream error: {str(e)}")
            return False
    
    def stop(self):
        if self.stream and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()
        self.stop_event.set()
    
    def display(self):
        audio_json = json.dumps(self.audio_data.tolist())
        components.html(f"""
        {self.visualizer_html}
        <script>
            audioData = {audio_json};
        </script>
        """, height=120)
    
    def __del__(self):
        self.stop()
        self.p.terminate()