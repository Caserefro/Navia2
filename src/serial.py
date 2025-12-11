import serial
import time

# --- CONFIGURATION ---
# Linux/Raspberry Pi uses /dev/ttyUSBx or /dev/ttyACMx
# Windows uses COMx (e.g., 'COM3')
SERIAL_PORT = '/dev/ttyUSB1'
BAUD_RATE = 115200


def read_from_esp32():
    try:
        print(f"Connecting to ESP32 on {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

        # Give the connection a second to settle
        time.sleep(2)
        print(f"Connected! Waiting for data...")

        while True:
            if ser.in_waiting > 0:
                # Read a line, decode bytes to string, strip whitespace
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(f"[ESP32] {line}")
                except UnicodeDecodeError:
                    # Sometimes you get garbage bytes on startup, ignore them
                    print("[RAW] (Decoding Error)")

    except serial.SerialException as e:
        print(f"Error: Could not open port {SERIAL_PORT}. Is it plugged in?")
        print(f"Details: {e}")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed.")


if __name__ == "__main__":
    read_from_esp32()