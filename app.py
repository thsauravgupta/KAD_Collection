import tkinter as tk
from tkinter import messagebox, scrolledtext
import speech_recognition as sr
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import os
import threading

# Recording parameters
RECORD_SECONDS = 3
SAMPLE_RATE = 16000


class AudioRecorder:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Recorder")
        self.root.geometry("600x400")
        self.root.resizable(False, False)

        # --- Speaker ID Entry ---
        tk.Label(root, text="Speaker ID:").pack(pady=5)
        self.speaker_entry = tk.Entry(root, width=30)
        self.speaker_entry.pack(pady=5)

        # --- Start/Stop Buttons ---
        self.start_btn = tk.Button(root, text="Start Listening", command=self.start_listening, bg="green", fg="white")
        self.start_btn.pack(pady=10)

        self.stop_btn = tk.Button(root, text="Stop", command=self.stop_listening, state=tk.DISABLED, bg="red", fg="white")
        self.stop_btn.pack(pady=5)

        # --- Log area ---
        self.log_area = scrolledtext.ScrolledText(root, width=70, height=15, state=tk.DISABLED)
        self.log_area.pack(pady=10)

        # Control flag for loop
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

    def listen_loop(self, speaker_id):
        recognizer = sr.Recognizer()
        microphone = sr.Microphone(sample_rate=SAMPLE_RATE)

        self.log(f"🎙️ Listening started for Speaker: '{speaker_id}'")
        self.log("Say a single word to trigger recording...")

        while self.listening:
            try:
                with microphone as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, phrase_time_limit=3)

                try:
                    recognized_text = recognizer.recognize_google(audio).lower()
                    self.log(f"🗣️ You said: '{recognized_text}'")

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

                except sr.UnknownValueError:
                    self.log("❌ Could not understand audio.")
                except sr.RequestError as e:
                    self.log(f"❌ API error: {e}")

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

        # Run in separate thread so GUI doesn’t freeze
        threading.Thread(target=self.listen_loop, args=(speaker_id,), daemon=True).start()

    def stop_listening(self):
        self.listening = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioRecorder(root)
    root.mainloop()
