import serial
import time
import threading
import sys

# --- CONFIGURATION ---
SERIAL_PORT = '/dev/ttyUSB1'  # Check if this is correct!
BAUD_RATE = 115200

# Global flag to control the loop
running = True


def read_thread(ser):
    """
    Runs in the background. Constantly checks for data from ESP32.
    """
    global running
    while running:
        try:
            if ser.in_waiting > 0:
                # Read line, replace errors so it doesn't crash on noise
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    # \r clears the current line so the input prompt doesn't get messy
                    # But if the ESP spams a lot, it will just scroll naturally
                    print(f"[ESP32] {line}")
            else:
                # Sleep briefly to save CPU
                time.sleep(0.01)

        except Exception as e:
            print(f"\n[Reader Error] {e}")
            break


def main():
    global running
    ser = None

    try:
        print(f"Connecting to {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Allow DTR reset to settle
        print("Connected! Type a command and press ENTER. (Ctrl+C to quit)")
        print("-" * 40)

        # 1. Start the Background Reader
        t = threading.Thread(target=read_thread, args=(ser,), daemon=True)
        t.start()

        # 2. Main Loop: Handles Writing
        while running:
            # Python's input() blocks until you hit Enter.
            # Because reading is in a thread, incoming data still prints!
            cmd = input()

            if cmd.lower() in ['exit', 'quit']:
                break

            if ser.is_open:
                # Add newline because Serial.readStringUntil('\n') expects it
                payload = cmd + "\n"