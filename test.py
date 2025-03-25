import streamlit as st
import os
import random
import time
import numpy as np
import queue
from threading import Thread, Event
from datetime import datetime
import sounddevice as sd
import soundfile as sf
import whisper

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 5
WHISPER_MODEL = "base"  # "tiny", "base", "small", "medium", "large"

# Theme structure
THEMES = {
    "German": {
        "Identitäten": ["Persönliche Attribute", "Persönliche Beziehungen", "Essen und Trinken", "Körperliches Wohlbefinden"],
        "Erfahrungen": ["Tägliche Routine", "Freizeit", "Ferien", "Feste und Feiern"],
        "Menschlicher Einfallsreichtum": ["Transport", "Unterhaltung", "Medien", "Technologie"],
        "Soziale Organisation": ["Nachbarschaft", "Bildung", "Arbeitsplatz", "Soziale Fragen"],
        "Den Planeten teilen": ["Klima", "Physische Geographie", "Umwelt", "Globale Themen"]
    },
    "Spanish": {
        "Identidades": ["Atributos personales", "Relaciones personales", "Comer y beber", "Bienestar físico"],
        "Experiencias": ["Rutina diaria", "Ocio", "Vacaciones", "Fiestas y celebraciones"],
        "Ingenio humano": ["Transporte", "Entretenimiento", "Medios de comunicación", "Tecnología"],
        "Organización social": ["Vecindario", "Educación", "Lugar de trabajo", "Cuestiones sociales"],
        "Compartir el planeta": ["Clima", "Geografía física", "Medio ambiente", "Temas globales"]
    }
}

# Initialize session state
def init_session_state():
    if 'page' not in st.session_state:
        st.session_state.page = 'language_selection'
    if 'language' not in st.session_state:
        st.session_state.language = None
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    if 'transcript' not in st.session_state:
        st.session_state.transcript = ""
    if 'selected_image' not in st.session_state:
        st.session_state.selected_image = None
    if 'saved_files' not in st.session_state:
        st.session_state.saved_files = []
    if 'exam_images' not in st.session_state:
        st.session_state.exam_images = None
    if 'whisper_model' not in st.session_state:
        st.session_state.whisper_model = None
    if 'audio_queue' not in st.session_state:
        st.session_state.audio_queue = queue.Queue()
    if 'stop_event' not in st.session_state:
        st.session_state.stop_event = Event()
    if 'listening_status' not in st.session_state:
        st.session_state.listening_status = "🔴 Not Listening"

# Audio callback
def audio_callback(indata, frames, time, status):
    if st.session_state.is_recording:
        st.session_state.audio_queue.put(indata.copy())

# Recording thread
def recording_thread():
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE,
                          channels=CHANNELS,
                          callback=audio_callback):
            st.session_state.listening_status = "🎤 Listening..."
            while not st.session_state.stop_event.is_set():
                time.sleep(0.1)
    except Exception as e:
        st.session_state.listening_status = f"⛔ Error: {str(e)}"
        st.session_state.is_recording = False

# Transcribe audio
def transcribe_audio():
    if st.session_state.whisper_model is None:
        st.session_state.whisper_model = whisper.load_model(WHISPER_MODEL)
    
    audio_data = []
    while not st.session_state.audio_queue.empty():
        audio_data.append(st.session_state.audio_queue.get())
    
    if audio_data:
        audio_data = np.concatenate(audio_data)
        temp_file = f"temp_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        sf.write(temp_file, audio_data, SAMPLE_RATE)
        
        result = st.session_state.whisper_model.transcribe(
            temp_file,
            language="de" if st.session_state.language == "German" else "es"
        )
        
        try:
            os.remove(temp_file)
        except:
            pass
        
        return result["text"]
    return None

# Recording page
def recording_page():
    st.title(f"{st.session_state.language} Speaking Exam")
    
    left_col, right_col = st.columns([1, 2])
    
    with left_col:
        st.image(os.path.join("uploads", st.session_state.selected_image['filename']), 
               use_container_width=True)
        
        status_color = "red" if "Error" in st.session_state.listening_status else "green"
        st.markdown(f"<p style='color:{status_color}; font-size:16px;'>{st.session_state.listening_status}</p>", 
                   unsafe_allow_html=True)
        
        if not st.session_state.is_recording:
            if st.button("🎤 Start Recording", type="primary", use_container_width=True):
                st.session_state.is_recording = True