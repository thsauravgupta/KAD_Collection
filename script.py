import speech_recognition as sr
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import os
import sys


RECORD_SECONDS = 3      
SAMPLE_RATE = 16000     

def save_recording(word, audio_data, speaker_id):
    os.makedirs(word, exist_ok=True)

    
    count = 1
    while True:
        
        file_path = os.path.join(word, f"{word}_{speaker_id}_{count}.wav")
        if not os.path.exists(file_path):
            break
        count += 1

    
    audio_data_int16 = np.int16(audio_data * 32767)
    write(file_path, SAMPLE_RATE, audio_data_int16)
    print(f"✅ Recording saved successfully to: {file_path}")

def main():
    
    speaker_id = input("Please enter the Speaker ID (e.g., s1, s2, user_a): ").strip()
    if not speaker_id:
        print(" Speaker ID cannot be empty. Exiting.")
        sys.exit()

    recognizer = sr.Recognizer()
    microphone = sr.Microphone(sample_rate=SAMPLE_RATE)

    print("\n--- Dynamic Audio Data Collection Script ---")
    print(f"✅ Session started for Speaker: '{speaker_id}'")
    print("Say any single word to trigger a recording.")
    print("Press Ctrl+C to stop the session.")
    print("-------------------------------------------\n")

    while True:
        try:
            with microphone as source:
                print(" Listening for a word...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source)

            try:
                recognized_text = recognizer.recognize_google(audio).lower()
                print(f" You said: '{recognized_text}'")

                if len(recognized_text.split()) == 1:
                    spoken_word = recognized_text
                    
                    print(f" Word '{spoken_word}' detected! Recording for {RECORD_SECONDS} seconds.")
                    
                    recording = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), 
                                       samplerate=SAMPLE_RATE, 
                                       channels=1, 
                                       dtype='float64')
                    sd.wait()

                    save_recording(spoken_word, recording, speaker_id)
                    print("\n-------------------------------------------\n")
                else:
                    print(" Please speak only a single, isolated word to trigger recording.")

            except sr.UnknownValueError:
                print("Could not understand audio. Please try again.")
            except sr.RequestError as e:
                print(f"Could not request results from Google's service; {e}")

        except KeyboardInterrupt:
            print(f"\n Session for speaker '{speaker_id}' ended. Exiting.")
            break

if __name__ == "__main__":
    main()