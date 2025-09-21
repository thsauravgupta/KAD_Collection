import tkinter as tk
from tkinter import messagebox, scrolledtext
import speech_recognition as sr
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import os
import threading
import tempfile

import whisper




# Recording parameters
RECORD_SECONDS = 3
SAMPLE_RATE = 16000


class AudioRecorder:
    def __init__(self, root):
        self.root = root
        self.root.title("🎙️ Audio Recorder")
        self.root.geometry("700x500")
        self.root.configure(bg="#f0f0f0")
        self.root.resizable(False, False)

        model_name = "openai/whisper-base"
        device = "cpu"
        self.model = whisper.load_model("large-v3")  # or "small" if you don't need Kashmiri

        # Set model to eval mode and move to device
        self.model.eval()
        self.model = self.model.to(device)

        header = tk.Label(root, text="Audio Recorder & Word Detector", 
                          font=("Arial", 18, "bold"), bg="#4CAF50", fg="white", pady=10)
        header.pack(fill="x")

        # --- Speaker ID Section ---
        frame_top = tk.Frame(root, bg="#f0f0f0")
        frame_top.pack(pady=15)

        tk.Label(frame_top, text="Speaker ID:", font=("Arial", 12), bg="#f0f0f0").grid(row=0, column=0, padx=5)
        self.speaker_entry = tk.Entry(frame_top, width=25, font=("Arial", 12))
        self.speaker_entry.grid(row=0, column=1, padx=5)

        frame_buttons = tk.Frame(root, bg="#f0f0f0")
        frame_buttons.pack(pady=10)

        self.start_btn = tk.Button(frame_buttons, text="▶ Start Listening", 
                                   command=self.start_listening, bg="#4CAF50", fg="white",
                                   font=("Arial", 12, "bold"), width=18, height=2)
        self.start_btn.grid(row=0, column=0, padx=10)

        self.stop_btn = tk.Button(frame_buttons, text="⏹ Stop", 
                                  command=self.stop_listening, state=tk.DISABLED, bg="#F44336", fg="white",
                                  font=("Arial", 12, "bold"), width=18, height=2)
        self.stop_btn.grid(row=0, column=1, padx=10)

        tk.Label(root, text="Logs / Output:", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(anchor="w", padx=15, pady=5)
        self.log_area = scrolledtext.ScrolledText(root, width=80, height=18, font=("Consolas", 10), state=tk.DISABLED)
        self.log_area.pack(padx=15, pady=5, fill="both", expand=True)

        self.listening = False


    def log(self, message):
        """Append text to log area."""
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def save_recording(self, word, audio_data, speaker_id):
        os.makedirs(word, exist_ok=True)

        count = 1
        while True:
            file_path = os.path.join(word, f"{word}_{speaker_id}_{count}.wav")
            if not os.path.exists(file_path):
                break
            count += 1

        audio_data_int16 = np.int16(audio_data * 32767)
        write(file_path, SAMPLE_RATE, audio_data_int16)
        self.log(f"✅ Recording saved successfully: {file_path}")

    def transcribe_with_whisper(self, audio_data):
        """Use OpenAI Whisper to translate Kashmiri speech into English"""
        # Save temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            audio_int16 = np.int16(audio_data * 32767)
            write(tmpfile.name, SAMPLE_RATE, audio_int16)
            tmp_path = tmpfile.name

        # Transcribe and translate using Whisper
        result = self.model.transcribe(tmp_path, task="translate", language="Kashmiri")
        text = result["text"].strip().lower()

        # Clean up temp file
        os.remove(tmp_path)
        return text


    def listen_loop(self, speaker_id):
        recognizer = sr.Recognizer()
        microphone = sr.Microphone(sample_rate=SAMPLE_RATE)

        self.log(f"🎙️ Listening started for Speaker: '{speaker_id}'")
        self.log("Say a single Kashmiri word to trigger recording...")

        while self.listening:
            try:
                with microphone as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, phrase_time_limit=3)

                # Convert raw audio
                audio_data = np.frombuffer(audio.get_raw_data(), np.int16).astype(np.float32) / 32767.0

                # --- Whisper translation ---
                recognized_text = self.transcribe_with_whisper(audio_data)
                self.log(f"🗣️ You said (translated): '{recognized_text}'")

                if len(recognized_text.split()) == 1:
                    self.log(f"Word '{recognized_text}' detected! Recording for {RECORD_SECONDS} seconds...")

                    recording = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE),
                                       samplerate=SAMPLE_RATE,
                                       channels=1,
                                       dtype='float64')
                    sd.wait()

                    self.save_recording(recognized_text, recording, speaker_id)
                    self.log("-------------------------------------------")
                else:
                    self.log("⚠️ Please speak only a single word.")

            except Exception as e:
                self.log(f"⚠️ Error: {e}")
                break

        self.log(f"🛑 Session for speaker '{speaker_id}' ended.")

    def start_listening(self):
        speaker_id = self.speaker_entry.get().strip()
        if not speaker_id:
            messagebox.showerror("Error", "Please enter a Speaker ID")
            return

        self.listening = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        threading.Thread(target=self.listen_loop, args=(speaker_id,), daemon=True).start()

    def stop_listening(self):
        self.listening = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioRecorder(root)
    root.mainloop()
