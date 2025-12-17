import asyncio
import websockets
import pygame
import math
import sys

# --- Configuration ---
WS_URL = "ws://10.250.18.141:8000"

DEADZONE = 0.15
ROTATION_STEP = 0.05
ROTATION_DECAY = 0.02
SEND_RATE = 0.02  # 50Hz
SMOOTH_ALPHA = 0.3  # Smoothing factor


# --- Utils ---
def deadzone(x):
    return 0.0 if abs(x) < DEADZONE else x


def normalize_vector(x, y):
    mag = math.sqrt(x * x + y * y)
    if mag > 1.0:
        return x / mag, y / mag
    return x, y


# --- Task: Joystick Controller ---
async def controller_loop(ws):
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller connected! (Waiting...)")
        # Keep task alive even if no controller, to allow console to work
        while True:
            await asyncio.sleep(1)

    js = pygame.joystick.Joystick(0)
    js.init()
    print(f"Using controller: {js.get_name()}")

    last_packet = ""
    smooth_x = 0.0
    smooth_y = 0.0
    rotation = 0.0

    while True:
        pygame.event.pump()

        # 1. Read Inputs
        lx = -deadzone(js.get_axis(0))
        ly = -deadzone(js.get_axis(1))  # Invert Y if needed for your robot

        # 2. Normalize
        nx, ny = normalize_vector(lx, ly)

        # 3. Smooth
        smooth_x = SMOOTH_ALPHA * nx + (1 - SMOOTH_ALPHA) * smooth_x
        smooth_y = SMOOTH_ALPHA * ny + (1 - SMOOTH_ALPHA) * smooth_y

        # 4. Rotation Logic
        if js.get_button(9):  # Right Shoulder (Verify ID)
            rotation += ROTATION_STEP
        if js.get_button(10):  # Left Shoulder (Verify ID)
            rotation -= ROTATION_STEP

        # Decay
        if not (js.get_button(9) or js.get_button(10)):
            if rotation > 0:
                rotation -= ROTATION_DECAY
                if rotation < 0: rotation = 0
            elif rotation < 0:
                rotation += ROTATION_DECAY
                if rotation > 0: rotation = 0

        rotation = max(-1.0, min(1.0, rotation))

        # 5. Send 'S' Packet (Speed)
        # Format: S,x,y,th
        packet = f"S,{smooth_x:.2f},{smooth_y:.2f},{rotation:.2f}"
        print(packet)
        if packet != last_packet:
            await ws.send(packet)
            last_packet = packet

        await asyncio.sleep(SEND_RATE)


# --- Task: Console Input ---
async def console_loop(ws):
    loop = asyncio.get_running_loop()
    print(">>> Console Ready. Type 'x,y,th' (e.g. 100,0,90) + Enter to send Position.")

    while True:
        # run_in_executor prevents input() from blocking the joystick
        user_input = await loop.run_in_executor(None, input)

        if not user_input.strip():
            continue

        # Format: P,x,y,th
        packet = f"P,{user_input.strip()}"
        print(f"Sending Manual Command: {packet}")

        await ws.send(packet)


# --- Main Connection Logic ---
async def main():
    while True:
        try:
            print(f"Connecting to {WS_URL}...")
            async with websockets.connect(WS_URL, ping_interval=None) as ws:
                print("Connected!")

                # Run both tasks simultaneously
                # valid_tasks ensures we handle exceptions (like disconnects) in either loop
                task_joystick = asyncio.create_task(controller_loop(ws))
                task_console = asyncio.create_task(console_loop(ws))

                # Wait until one task fails (usually connection dropped in controller_loop)
                done, pending = await asyncio.wait(
                    [task_joystick, task_console],
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Cancel the pending task (e.g. if joystick failed, stop console listener)
                for task in pending:
                    task.cancel()

        except (OSError, websockets.exceptions.ConnectionClosed) as e:
            print(f"Connection lost/failed: {e}")
            print("Retrying in 2 seconds...")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Unexpected error: {e}")
            await asyncio.sleep(2)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")