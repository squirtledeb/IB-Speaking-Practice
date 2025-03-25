import streamlit as st
import os
import random
import time
import speech_recognition as sr
from threading import Thread, Lock
from queue import Queue
from audio_visualizer import AudioVisualizer

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

# Global variables for thread-safe operations
transcript_queue = Queue()
mic_lock = Lock()
recording_thread = None

def init_session_state():
    required_state = {
        'page': 'language_selection',
        'language': None,
        'is_recording': False,
        'transcript': "",
        'start_time': 0,
        'selected_image': None,
        'saved_files': [],
        'visualizer': None,
        'last_audio_time': 0,
        'exam_images': None  # Store the randomly selected exam images
    }
    for key, value in required_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

def recognition_thread():
    recognizer = sr.Recognizer()
    with mic_lock:
        try:
            with sr.Microphone() as source:
                print("Microphone initialized - Speak now!")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                
                while st.session_state.is_recording:
                    try:
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                        text = recognizer.recognize_google(audio, 
                            language="es-ES" if st.session_state.language == "Spanish" else "de-DE")
                        print(f"Recognized: {text}")
                        transcript_queue.put(text)
                        st.session_state.last_audio_time = time.time()
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        transcript_queue.put("(Listening...)")
                    except Exception as e:
                        transcript_queue.put(f"[Error: {str(e)}]")
                        break
        except Exception as e:
            transcript_queue.put(f"[Microphone Error: {str(e)}]")
            st.session_state.is_recording = False

def recording_page():
    st.title(f"{st.session_state.language} Speaking Exam")
    
    if st.session_state.visualizer is None:
        st.session_state.visualizer = AudioVisualizer()
    
    left_col, right_col = st.columns([1, 2])
    
    with left_col:
        st.image(os.path.join("uploads", st.session_state.selected_image['filename']), 
               use_container_width=True)
        
        st.session_state.visualizer.display()
        
        if not st.session_state.is_recording:
            if st.button("🎤 Start Recording", type="primary", use_container_width=True):
                st.session_state.is_recording = True
                st.session_state.start_time = time.time()
                st.session_state.transcript = ""
                st.session_state.visualizer.start()
                global recording_thread
                recording_thread = Thread(target=recognition_thread, daemon=True)
                recording_thread.start()
        else:
            elapsed = time.time() - st.session_state.start_time
            st.metric("Recording Time", time.strftime("%M:%S", time.gmtime(elapsed)))
            if st.button("⏹ Stop Recording", type="secondary", use_container_width=True):
                st.session_state.is_recording = False
                st.session_state.visualizer.stop()
                st.session_state.start_time = 0  # Reset timer
                st.rerun()
    
    with right_col:
        st.subheader("Live Transcript")
        
        # Process any new transcript items
        while not transcript_queue.empty():
            new_text = transcript_queue.get()
            st.session_state.transcript += new_text + " "
            print(f"Transcript: {st.session_state.transcript}")  # Debug
        
        # Display transcript with clear styling
        st.markdown(
            f'<div style="background: white; padding: 20px; border-radius: 10px; '
            f'min-height: 300px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); '
            f'color: #000000; font-size: 16px; line-height: 1.6; white-space: pre-wrap;">'
            f'{st.session_state.transcript}'
            f'</div>',
            unsafe_allow_html=True
        )
        # Auto-refresh when recording
        if st.session_state.is_recording:
            time.sleep(0.3)
            st.rerun()

def main():
    st.set_page_config(page_title="IB Speaking Practice", layout="centered")
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
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.page == "language_selection":
        st.session_state.exam_images = None  # Reset exam images when selecting language
        st.title("IB Speaking Practice")
        st.session_state.language = st.selectbox("Select Language", ["German", "Spanish"])
        if st.button("Continue"):
            st.session_state.page = "image_upload"
            st.rerun()
    
    elif st.session_state.page == "image_upload":
        st.session_state.exam_images = None  # Reset exam images when uploading new images
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
    
    elif st.session_state.page == "exam":
        st.title("Exam Time")
        st.write("Describe one of these images:")
        
        # Only generate new random images if we don't have them yet
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
        
        # Display the stored images (not newly generated ones)
        if st.session_state.exam_images:
            cols = st.columns(2)
            for i, img in enumerate(st.session_state.exam_images):
                with cols[i]:
                    st.image(os.path.join("uploads", img["filename"]), 
                            use_container_width=True)
                    if st.button(f"Describe this {img['theme']} image", key=f"img_{i}"):
                        st.session_state.selected_image = img
                        st.session_state.page = "recording"
                        st.session_state.exam_images = None  # Reset for next time
                        st.rerun()
    
    elif st.session_state.page == "recording":
        recording_page()

if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    main()