import tkinter as tk
from tkinter import messagebox, font
import threading
import os
import re
import time
import pyaudio
import wave

# --- Configuration ---
# Audio recording settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000   # Force 16kHz
CHUNK = 1024
TEMP_WAVE_FILENAME = "temp_recording.wav"

class AudioRecorderApp:
    """
    A tkinter application for recording audio, assigning it to a user-provided
    word name (used as folder name), and saving the audio file there.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Word Audio Logger")
        self.root.geometry("550x400")
        self.root.configure(bg="#f0f0f0")

        # --- State Variables ---
        self.is_recording = False
        self.audio_frames = []

        # --- Audio Setup ---
        self.p = pyaudio.PyAudio()
        self.stream = None

        # --- UI Setup ---
        self.setup_ui()

    def setup_ui(self):
        """Creates and arranges all the widgets in the main window."""
        main_font = font.Font(family="Helvetica", size=10)
        status_font = font.Font(family="Helvetica", size=11, weight="bold")

        # --- Main Frame ---
        main_frame = tk.Frame(self.root, bg="#f0f0f0", padx=20, pady=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Speaker Name ---
        speaker_frame = tk.Frame(main_frame, bg="#f0f0f0")
        speaker_frame.pack(pady=(0, 10), fill=tk.X)
        tk.Label(speaker_frame, text="Speaker Name:", font=main_font, bg="#f0f0f0").pack(side=tk.LEFT, padx=(0, 10))
        self.speaker_name_var = tk.StringVar(value="speaker1")
        tk.Entry(speaker_frame, textvariable=self.speaker_name_var, font=main_font, width=40).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # --- Word Name (User Input for Folder) ---
        word_frame = tk.Frame(main_frame, bg="#f0f0f0")
        word_frame.pack(pady=(0, 20), fill=tk.X)
        tk.Label(word_frame, text="Word Name (Folder):", font=main_font, bg="#f0f0f0").pack(side=tk.LEFT, padx=(0, 10))
        self.word_name_var = tk.StringVar(value="word1")
        tk.Entry(word_frame, textvariable=self.word_name_var, font=main_font, width=40).pack(side=tk.LEFT, expand=True, fill=tk.X)

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
        
        # Start recording in a separate thread
        self.recording_thread = threading.Thread(target=self.record_audio_thread)
        self.recording_thread.start()

    def stop_recording(self):
        """Stops the recording and saves to a temp file."""
        self.is_recording = False
        self.record_button.config(text="Record", bg="#4CAF50")
        self.status_label.config(text="Processing audio...", fg="orange")
        self.root.update()
        
        # Wait a moment then process
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
        """Saves the recorded audio to a temporary file."""
        if not self.audio_frames:
            self.status_label.config(text="No audio recorded.", fg="red")
            return

        wf = wave.open(TEMP_WAVE_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(self.audio_frames))
        wf.close()

        self.status_label.config(text="Ready to save.", fg="green")
        self.save_button.config(state=tk.NORMAL)
        self.rerecord_button.config(state=tk.NORMAL)

    def re_record(self):
        """Resets the state to allow for a new recording."""
        self.is_recording = False
        self.audio_frames = []

        self.status_label.config(text="Ready to record", fg="#333")
        self.record_button.config(text="Record", bg="#4CAF50", state=tk.NORMAL)
        self.rerecord_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        
        if os.path.exists(TEMP_WAVE_FILENAME):
            os.remove(TEMP_WAVE_FILENAME)

    def save_audio(self):
        """Saves the audio file to the specified word folder with incremental numbering."""
        word_name = self.word_name_var.get().strip().lower()  # trim + lowercase
        speaker = self.speaker_name_var.get().strip().lower() or "speaker"  # trim + lowercase

        if not word_name or not os.path.exists(TEMP_WAVE_FILENAME):
            messagebox.showwarning("Warning", "No valid recording or word name.")
            return

        # Sanitize inputs (remove non-alphanumeric characters)
        folder_name = re.sub(r'\W+', '', word_name)
        speaker = re.sub(r'\W+', '', speaker)

        try:
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)

            # Find existing files for this speaker and word
            existing_files = [
                f for f in os.listdir(folder_name)
                if f.startswith(f"{speaker}_{folder_name}_") and f.endswith(".wav")
            ]

            # Extract numbers from existing files
            numbers = []
            for f in existing_files:
                match = re.match(rf"{speaker}_{folder_name}_(\d+)\.wav", f)
                if match:
                    numbers.append(int(match.group(1)))

            next_num = max(numbers, default=0) + 1  # increment based on last number

            filename = f"{speaker}_{folder_name}_{next_num}.wav"
            final_path = os.path.join(folder_name, filename)

            os.rename(TEMP_WAVE_FILENAME, final_path)

            messagebox.showinfo("Success", f"Audio saved successfully to:\n{final_path}")
            self.re_record()

        except Exception as e:
            messagebox.showerror("Error", f"Could not save the file: {e}")


    def on_closing(self):
        """Handles cleanup when the window is closed."""
        if self.is_recording:
            self.is_recording = False
        self.p.terminate()
        if os.path.exists(TEMP_WAVE_FILENAME):
            os.remove(TEMP_WAVE_FILENAME)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioRecorderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
