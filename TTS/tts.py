#!/usr/bin/env python3
"""
Piper TTS 
"""

import os
import sys
from piper import PiperVoice
import pyaudio
import numpy as np
import socket

HOST = "192.168.128.1" # laptop IP on CPPGuest I think, 10.42.0.169 is laptop IP on spotpi wifi
PORT = 852

def find_voice(model_name="en_US-arctic-medium"):
    voice_dir = "./piper-voices"
    voice_path = os.path.join(voice_dir, f"{model_name}.onnx")
    
    if os.path.exists(voice_path):
        print(f" Found: {voice_path}")
        return voice_path
    
    for base in ["~/.local/share/piper-voices", "./"]:
        full = os.path.expanduser(os.path.join(base, f"{model_name}.onnx"))
        if os.path.exists(full):
            print(f"✅ Found: {full}")
            return full
    
    raise FileNotFoundError(f"Voice '{model_name}' not in piper-voices/")

# Load voice
voice = PiperVoice.load(find_voice())

# Audio setup
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=22050, output=True)

def speak(text):
    for chunk in voice.synthesize(text):
        stream.write(chunk.audio_int16_bytes)
    stream.stop_stream(); stream.start_stream()  # Clear stream

# Main
if __name__ == "__main__":
    print("Piper TTS Ready")
    speak("Ready to go!")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print(f"🔗 Connecting to {HOST}:{PORT}...")
            s.connect((HOST, PORT))
            print("✅ Connected to server!")
            
            while True:  # Continuous loop
                try:
                    data = s.recv(1024)
                    if not data:
                        print("👋 Server disconnected")
                        break
                    
                    text = data.decode('utf-8', errors='ignore').strip()
                    if text:
                        print(f"📨 Server: {text}")
                        speak(text)
                        
                except socket.timeout:
                    continue
                except ConnectionResetError:
                    print("❌ Server closed connection")
                    break
                    
    except ConnectionRefusedError:
        print("❌ Connection refused - start host.py first!")
    except KeyboardInterrupt:
        print("\n👋 Client stopped")
    finally:
        print("🔇 Closing audio...")
        stream.stop_stream()
        stream.close()
        p.terminate()

    """ Was for voice testing
    print("\nInteractive mode (Ctrl+C to quit):")
    try:
        while True:
            text = input("> ")
            if text.lower() in ['quit', 'exit', 'bye']:
                break
            speak(text)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    finally:
        stream.close()
        p.terminate()
    """