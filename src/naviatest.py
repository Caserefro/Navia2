import queue
import threading
import sounddevice as sd
from faster_whisper import WhisperModel
import numpy as np
import time

# -----------------------------
# Settings
# -----------------------------
SAMPLE_RATE = 16000
BLOCK_SIZE = 1024
CHUNK_DURATION = 1.0   # seconds of audio per transcription call
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION)

audio_q = queue.Queue()

# -----------------------------
# Load model
# -----------------------------
print("Loading model…")
model = WhisperModel("small", device="cpu", compute_type="int8")

# -----------------------------
# Audio callback
# -----------------------------
def audio_callback(indata, frames, time_info, status):
    if status:
        print("Audio status:", status)
    audio_q.put(indata.copy().flatten())


# -----------------------------
# Transcription thread
# -----------------------------
def transcribe_loop():
    print("Listening…")

    buffer = np.zeros((0,), dtype=np.float32)

    while True:
        # Wait for audio from callback
        block = audio_q.get()
        buffer = np.concatenate((buffer, block))

        # If we have enough audio, transcribe it
        if len(buffer) >= CHUNK_SAMPLES:
            chunk = buffer[:CHUNK_SAMPLES]
            buffer = buffer[CHUNK_SAMPLES:]

            print("Transcribing…")
            t0 = time.time()
            segments, info = model.transcribe(chunk, language="es", beam_size=1)
            t1 = time.time()

            print(f"⏱ {t1 - t0:.3f}s")

            for seg in segments:
                print(f"🗣 {seg.text}")


# -----------------------------
# Start everything
# -----------------------------
threading.Thread(target=transcribe_loop, daemon=True).start()

with sd.InputStream(
    samplerate=SAMPLE_RATE,
    blocksize=BLOCK_SIZE,
    channels=1,
    dtype="float32",
    callback=audio_callback
):
    print("Mic active. Speak.")
    while True:
        time.sleep(1)
