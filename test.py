import streamlit as st
import os
import random
import time
import whisper
from threading import Thread, Event
from queue import Queue
import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime

# Disable Streamlit's file watcher for PyTorch
os.environ["STREAMLIT_SERVER_ENABLE_STATIC_FILE_WATCHER"] = "false"

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

# Audio configuration
SAMPLE_RATE = 16000
CHANNELS = 1
audio_queue = Queue()
transcript_queue = Queue()
stop_event = Event()
whisper_model = None
audio_stream = None

def init_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.update({
            'initialized': True,
            'page': 'language_selection',
            'language': None,
            'is_recording': False,
            'transcript': "",
            'start_time': 0,
            'selected_image': None,
            'saved_files': [],
            'exam_images': None,
            'listening_status': "🔴 Not Listening",
            'last_update': 0
        })

def audio_callback(indata, frames, time, status):
    """Callback for audio input stream"""
    if st.session_state.is_recording:
        audio_queue.put(indata.copy())

def cleanup_audio():
    """Properly clean up audio resources"""
    global audio_stream
    if audio_stream is not None:
        try:
            if audio_stream.active:
                audio_stream.stop()
            if not audio_stream.closed:
                audio_stream.close()
        except:
            pass
        audio_stream = None

def recognition_thread():
    """Thread that handles speech recognition"""
    global whisper_model
    
    try:
        if whisper_model is None:
            whisper_model = whisper.load_model("base")
        
        st.session_state.listening_status = "🎤 Initializing..."
        
        while not stop_event.is_set():
            try:
                # Collect audio chunks for 3 seconds
                audio_chunks = []
                start_time = time.time()
                
                while time.time() - start_time < 3 and not stop_event.is_set():
                    if not audio_queue.empty():
                        chunk = audio_queue.get()
                        audio_chunks.append(chunk)
                    time.sleep(0.1)
                
                if not audio_chunks:
                    st.session_state.listening_status = "🔇 No audio detected"
                    continue
                    
                # Combine audio chunks
                audio_data = np.concatenate(audio_chunks)
                
                # Save temporary audio file
                temp_file = f"temp_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                sf.write(temp_file, audio_data, SAMPLE_RATE)
                
                st.session_state.listening_status = "🎤 Processing..."
                
                # Transcribe with Whisper
                result = whisper_model.transcribe(
                    temp_file,
                    language="de" if st.session_state.language == "German" else "es",
                    fp16=False
                )
                
                text = result["text"].strip()
                
                # Clean up
                try:
                    os.remove(temp_file)
                except:
                    pass
                
                if text:
                    transcript_queue.put(text)
                    st.session_state.listening_status = "🎤 Listening..."
                else:
                    st.session_state.listening_status = "❓ No speech detected"
                    
            except Exception as e:
                print(f"Recognition error: {e}")
                transcript_queue.put(f"[Error: {str(e)}]")
                st.session_state.listening_status = "⛔ Error"
                break
    finally:
        cleanup_audio()

def recording_page():
    """Main recording interface"""
    st.title(f"{st.session_state.language} Speaking Exam")
    
    left_col, right_col = st.columns([1, 2])
    
    with left_col:
        st.image(os.path.join("uploads", st.session_state.selected_image['filename']), 
               use_container_width=True)
        
        # Status indicator
        status_color = "red" if "Error" in st.session_state.listening_status else "green"
        st.markdown(f"<p style='color:{status_color}; font-size:16px;'>{st.session_state.listening_status}</p>", 
                   unsafe_allow_html=True)
        
        if not st.session_state.is_recording:
            if st.button("🎤 Start Recording", type="primary", use_container_width=True):
                st.session_state.is_recording = True
                st.session_state.start_time = time.time()
                st.session_state.transcript = ""
                st.session_state.listening_status = "🎤 Starting..."
                stop_event.clear()
                
                # Start audio stream
                global audio_stream
                cleanup_audio()  # Ensure clean state
                audio_stream = sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    callback=audio_callback,
                    blocksize=4096
                )
                audio_stream.start()
                
                # Start recognition thread
                Thread(target=recognition_thread, daemon=True).start()
        else:
            elapsed = time.time() - st.session_state.start_time
            st.metric("Recording Time", f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}")
            if st.button("⏹ Stop Recording", type="secondary", use_container_width=True):
                st.session_state.is_recording = False
                stop_event.set()
                cleanup_audio()
                st.rerun()
    
    with right_col:
        st.subheader("Live Transcript")
        transcript_display = st.empty()
        
        # Get new transcript text
        new_text = []
        while not transcript_queue.empty():
            new_text.append(transcript_queue.get())
        
        if new_text:
            st.session_state.transcript += " ".join(new_text) + " "
        
        # Update display
        transcript_display.text_area(
            "Transcript",
            value=st.session_state.transcript,
            height=400,
            key=f"transcript_{time.time()}"
        )
        
        # Auto-refresh
        if st.session_state.is_recording:
            time.sleep(0.3)
            st.rerun()

def language_selection_page():
    st.session_state.exam_images = None
    st.title("IB Speaking Practice")
    st.session_state.language = st.selectbox("Select Language", ["German", "Spanish"])
    if st.button("Continue"):
        st.session_state.page = "image_upload"
        st.rerun()

def image_upload_page():
    st.session_state.exam_images = None
    st.title("Upload Images")
    st.write("Upload 2-15 images with their themes:")
    
    uploaded_files = st.file_uploader("Choose images", type=["jpg", "jpeg", "png"], 
                                   accept_multiple_files=True)
    
    if uploaded_files:
        if len(uploaded_files) < 2:
            st.error("Please upload at least 2 images")
        elif len(uploaded_files) > 15:
            st.error("Maximum 15 images allowed")
        else:
            if not os.path.exists("uploads"):
                os.makedirs("uploads")
            
            st.session_state.saved_files = []
            for i, file in enumerate(uploaded_files):
                cols = st.columns([1, 3])
                with cols[0]:
                    st.image(file, use_container_width=True)
                with cols[1]:
                    theme = st.selectbox(
                        f"Theme for Image {i+1}",
                        options=list(THEMES[st.session_state.language].keys()),
                        key=f"theme_{file.name}"
                    )
                    file_path = os.path.join("uploads", file.name)
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())
                    st.session_state.saved_files.append({
                        "filename": file.name,
                        "theme": theme
                    })
            
            if st.button("Begin Exam"):
                st.session_state.page = "exam"
                st.rerun()

def exam_page():
    st.title("Exam Time")
    st.write("Describe one of these images:")
    
    if st.session_state.exam_images is None:
        themes = list(set([f["theme"] for f in st.session_state.saved_files]))
        if len(themes) >= 2:
            selected_themes = random.sample(themes, 2)
            st.session_state.exam_images = [
                random.choice([f for f in st.session_state.saved_files 
                              if f["theme"] == theme]) 
                for theme in selected_themes
            ]
        else:
            st.error("Need images from at least 2 different themes")
            st.session_state.page = "image_upload"
            st.rerun()
    
    if st.session_state.exam_images:
        cols = st.columns(2)
        for i, img in enumerate(st.session_state.exam_images):
            with cols[i]:
                st.image(os.path.join("uploads", img["filename"]), 
                        use_container_width=True)
                if st.button(f"Describe this {img['theme']} image", key=f"img_{i}"):
                    st.session_state.selected_image = img
                    st.session_state.page = "recording"
                    st.session_state.exam_images = None
                    st.rerun()

def main():
    st.set_page_config(
        page_title="IB Speaking Practice", 
        layout="centered",
        page_icon="🎤"
    )
    init_session_state()
    
    st.markdown("""
    <style>
        .stButton>button {
            border-radius: 20px;
            padding: 10px 24px;
        }
        .stImage {
            border-radius: 10px;
        }
        textarea {
            font-size: 16px !important;
            line-height: 1.6 !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 24px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.page == "language_selection":
        language_selection_page()
    elif st.session_state.page == "image_upload":
        image_upload_page()
    elif st.session_state.page == "exam":
        exam_page()
    elif st.session_state.page == "recording":
        recording_page()

if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    try:
        main()
    except Exception as e:
        print(f"Application error: {e}")
    finally:
        stop_event.set()
        cleanup_audio()