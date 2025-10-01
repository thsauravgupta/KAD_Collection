import tkinter as tk
from tkinter import messagebox, font
import threading
import os
import re
import time

# Attempt to import necessary libraries and guide the user if they are missing.
try:
    import pyaudio
    import wave
    import speech_recognition as sr
    import translators as ts
except ImportError:
    messagebox.showerror(
        "Missing Libraries",
        "Some required libraries are not installed.\n\nPlease run the following command in your terminal:\n\n"
        "pip install pyaudio SpeechRecognition translators"
    )
    exit()

# --- Configuration ---
# Audio recording settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
TEMP_WAVE_FILENAME = "temp_recording.wav"

class AudioRecorderApp:
    """
    A tkinter application for recording Kashmiri audio, transcribing it,
    translating the transcription to English, and saving the audio file
    in a directory named after the English translation.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Kashmiri Audio Logger")
        self.root.geometry("550x450")
        self.root.configure(bg="#f0f0f0")

        # --- State Variables ---
        self.is_recording = False
        self.audio_frames = []
        self.last_english_word = ""
        self.last_kashmiri_word = ""

        # --- Audio Setup ---
        self.p = pyaudio.PyAudio()
        self.stream = None

        # --- UI Setup ---
        self.setup_ui()

    def setup_ui(self):
        """Creates and arranges all the widgets in the main window."""
        main_font = font.Font(family="Helvetica", size=10)
        title_font = font.Font(family="Helvetica", size=14, weight="bold")
        status_font = font.Font(family="Helvetica", size=11, weight="bold")

        # --- Main Frame ---
        main_frame = tk.Frame(self.root, bg="#f0f0f0", padx=20, pady=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Speaker Name ---
        speaker_frame = tk.Frame(main_frame, bg="#f0f0f0")
        speaker_frame.pack(pady=(0, 20), fill=tk.X)
        tk.Label(speaker_frame, text="Speaker Name:", font=main_font, bg="#f0f0f0").pack(side=tk.LEFT, padx=(0, 10))
        self.speaker_name_var = tk.StringVar(value="speaker1")
        tk.Entry(speaker_frame, textvariable=self.speaker_name_var, font=main_font, width=40).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # --- Recording Controls ---
        controls_frame = tk.Frame(main_frame, bg="#f0f0f0")
        controls_frame.pack(pady=10)

        self.record_button = tk.Button(controls_frame, text="Record", command=self.toggle_recording, font=main_font, bg="#4CAF50", fg="white", width=12, height=2)
        self.record_button.pack(side=tk.LEFT, padx=5)

        self.rerecord_button = tk.Button(controls_frame, text="Re-record", command=self.re_record, font=main_font, bg="#f44336", fg="white", width=12, height=2, state=tk.DISABLED)
        self.rerecord_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = tk.Button(main_frame, text="Save Audio", command=self.save_audio, font=main_font, bg="#2196F3", fg="white", width=15, height=2, state=tk.DISABLED)
        self.save_button.pack(pady=(10, 20))


        # --- Status Display ---
        self.status_label = tk.Label(main_frame, text="Ready to record", font=status_font, bg="#e0e0e0", fg="#333", relief="sunken", bd=2, pady=10)
        self.status_label.pack(fill=tk.X, pady=10)
        
        # --- Transcription and Translation Display ---
        result_frame = tk.Frame(main_frame, bg="#ffffff", bd=2, relief="groove")
        result_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        tk.Label(result_frame, text="Transcription (Kashmiri):", font=main_font, bg="#ffffff", anchor="w").pack(fill=tk.X, padx=10, pady=(10,0))
        self.kashmiri_text_label = tk.Label(result_frame, text="...", font=main_font, bg="#ffffff", fg="navy", wraplength=450, anchor="w", justify=tk.LEFT)
        self.kashmiri_text_label.pack(fill=tk.X, padx=10, pady=(0,10))

        tk.Label(result_frame, text="Translation (English Folder Name):", font=main_font, bg="#ffffff", anchor="w").pack(fill=tk.X, padx=10, pady=(5,0))
        self.english_text_label = tk.Label(result_frame, text="...", font=main_font, bg="#ffffff", fg="green", wraplength=450, anchor="w", justify=tk.LEFT)
        self.english_text_label.pack(fill=tk.X, padx=10, pady=(0,10))


    def toggle_recording(self):
        """Starts or stops the audio recording."""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        """Begins the recording process."""
        self.is_recording = True
        self.audio_frames = []
        self.record_button.config(text="Stop", bg="#E57373")
        self.rerecord_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        self.status_label.config(text="Recording... Speak now.", fg="red")
        
        # Clear previous results
        self.kashmiri_text_label.config(text="...")
        self.english_text_label.config(text="...")
        
        # Start recording in a separate thread
        self.recording_thread = threading.Thread(target=self.record_audio_thread)
        self.recording_thread.start()

    def stop_recording(self):
        """Stops the recording and starts processing."""
        self.is_recording = False # This flag will stop the thread's loop
        self.record_button.config(text="Record", bg="#4CAF50")
        self.status_label.config(text="Processing audio...", fg="orange")
        self.root.update() # Force UI update
        
        # The thread will finish, then we process the audio
        # We add a small delay to ensure thread has stopped writing frames
        self.root.after(100, self.process_audio)
        
    def record_audio_thread(self):
        """The actual audio recording logic that runs in a thread."""
        self.stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        while self.is_recording:
            data = self.stream.read(CHUNK)
            self.audio_frames.append(data)
        self.stream.stop_stream()
        self.stream.close()

    def process_audio(self):
        """Saves the recorded audio to a temporary file and transcribes it."""
        if not self.audio_frames:
            self.status_label.config(text="No audio recorded.", fg="red")
            return

        # Save to a temporary wave file
        wf = wave.open(TEMP_WAVE_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(self.audio_frames))
        wf.close()
        
        self.transcribe_and_translate()

    def transcribe_and_translate(self):
        """Uses SpeechRecognition and translators to process the audio file."""
        r = sr.Recognizer()
        try:
            with sr.AudioFile(TEMP_WAVE_FILENAME) as source:
                audio_data = r.record(source)
                # Recognize speech using Google Web Speech API for Kashmiri
                self.last_kashmiri_word = r.recognize_google(audio_data, language='ks-IN')
                self.kashmiri_text_label.config(text=self.last_kashmiri_word)
                
                # Translate the text to English
                translated_text = ts.translate_text(self.last_kashmiri_word, from_language='auto', to_language='en')
                # Sanitize for folder name: lowercase, no spaces, only letters
                self.last_english_word = re.sub(r'[^a-z]', '', translated_text.lower())
                self.english_text_label.config(text=self.last_english_word)

                self.status_label.config(text="Ready to save.", fg="green")
                self.save_button.config(state=tk.NORMAL)
                self.rerecord_button.config(state=tk.NORMAL)

        except sr.UnknownValueError:
            self.status_label.config(text="Speech Recognition could not understand audio.", fg="red")
            self.rerecord_button.config(state=tk.NORMAL)
        except sr.RequestError as e:
            self.status_label.config(text=f"API error: {e}", fg="red")
            self.rerecord_button.config(state=tk.NORMAL)
        except Exception as e:
            self.status_label.config(text=f"An error occurred: {e}", fg="red")
            self.rerecord_button.config(state=tk.NORMAL)

    def re_record(self):
        """Resets the state to allow for a new recording."""
        self.is_recording = False
        self.audio_frames = []
        self.last_english_word = ""
        self.last_kashmiri_word = ""

        self.kashmiri_text_label.config(text="...")
        self.english_text_label.config(text="...")
        self.status_label.config(text="Ready to record", fg="#333")
        self.record_button.config(text="Record", bg="#4CAF50", state=tk.NORMAL)
        self.rerecord_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        
        if os.path.exists(TEMP_WAVE_FILENAME):
            os.remove(TEMP_WAVE_FILENAME)

    def save_audio(self):
        """Saves the audio file to the appropriate folder."""
        if not self.last_english_word or not os.path.exists(TEMP_WAVE_FILENAME):
            messagebox.showwarning("Warning", "No valid recording to save.")
            return
            
        folder_name = self.last_english_word
        speaker = self.speaker_name_var.get() or "speaker"
        speaker = re.sub(r'\W+', '', speaker) # Sanitize speaker name
        
        try:
            # Create directory if it doesn't exist
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)
                print(f"Created directory: {folder_name}")

            # Create a unique filename
            timestamp = int(time.time())
            filename = f"{speaker}_{self.last_english_word}_{timestamp}.wav"
            final_path = os.path.join(folder_name, filename)

            # Move the temporary file to the final destination
            os.rename(TEMP_WAVE_FILENAME, final_path)
            
            messagebox.showinfo("Success", f"Audio saved successfully to:\n{final_path}")
            self.re_record() # Reset for the next recording

        except Exception as e:
            messagebox.showerror("Error", f"Could not save the file: {e}")

    def on_closing(self):
        """Handles cleanup when the window is closed."""
        if self.is_recording:
            self.is_recording = False # Stop any active recording
        
        self.p.terminate()
        if os.path.exists(TEMP_WAVE_FILENAME):
            os.remove(TEMP_WAVE_FILENAME)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioRecorderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

