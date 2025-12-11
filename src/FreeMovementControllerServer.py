import asyncio
import math
import sys

import pygame
import websockets

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

DEADZONE = 0.15
ROTATION_STEP = 0.05
ROTATION_DECAY = 0.02
SEND_RATE = 0.02  # 50Hz (20ms)
SMOOTH_ALPHA = 0.3

connected_clients = set()


# ---------------------- Utils ----------------------
def deadzone(x):
    return 0.0 if abs(x) < DEADZONE else x


def normalize_vector(x, y):
    mag = math.sqrt(x * x + y * y)
    if mag > 1.0:
        return x / mag, y / mag
    return x, y


# ---------------------- WS Handler ----------------------
async def handler(ws):
    print(f"ESP32 connected: {ws.remote_address}")
    connected_clients.add(ws)
    try:
        async for msg in ws:
            # Print incoming messages from ESP32
            print(f"\n[ESP32 → PC] {msg}")
    except websockets.ConnectionClosed:
        print("ESP32 disconnected")
    finally:
        connected_clients.remove(ws)


# ---------------------- Console Input Loop ----------------------
async def console_loop():
    """
    Reads keyboard input without blocking the joystick loop.
    Expects user to type coordinates like: 100,200,90
    Sends: P,100,200,90
    """
    loop = asyncio.get_running_loop()
    print(">>> Console Ready. Type 'x,y,th' (e.g., 10,0,90) and hit Enter to send Position command.")

    while True:
        # run_in_executor prevents input() from freezing the joystick logic
        user_input = await loop.run_in_executor(None, input)

        if not user_input.strip():
            continue

        # Create packet with 'P' prefix
        packet = f"P,{user_input.strip()}"
        print(f"Sending Manual Command: {packet}")

        if connected_clients:
            try:
                await asyncio.gather(*[
                    ws.send(packet) for ws in connected_clients
                ])
            except Exception as e:
                print(f"Console Send Error: {e}")
        else:
            print("No ESP32 connected. Command ignored.")


# ---------------------- Joystick Loop ----------------------
async def controller_loop():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller found! (Only console mode active)")
        # We don't return here anymore, or the task dies.
        # Instead we just wait forever so the console still works.
        while True:
            await asyncio.sleep(1)

    js = pygame.joystick.Joystick(0)
    js.init()
    print(f"Using controller: {js.get_name()}")

    last_packet = ""
    x_s = y_s = 0.0
    th = 0.0

    while True:
        pygame.event.pump()

        # Left stick → x,y
        lx = deadzone(js.get_axis(0))
        ly = -deadzone(js.get_axis(1))
        nx, ny = normalize_vector(lx, ly)

        # Smooth
        x_s = SMOOTH_ALPHA * nx + (1 - SMOOTH_ALPHA) * x_s
        y_s = SMOOTH_ALPHA * ny + (1 - SMOOTH_ALPHA) * y_s

        # Rotation (Shoulder buttons)
        if js.get_button(9): th += ROTATION_STEP  # R1
        if js.get_button(10): th -= ROTATION_STEP  # L1

        # Decay
        if not (js.get_button(9) or js.get_button(10)):
            if th > 0:
                th -= ROTATION_DECAY
                if th < 0: th = 0
            elif th < 0:
                th += ROTATION_DECAY
                if th > 0: th = 0

        th = max(-1.0, min(1.0, th))

        # *** Modified Packet Format ***
        # Prefixed with S (Speed)
        packet = f"S,{-x_s:.2f},{y_s:.2f},{th:.2f}"

        # Send only if changed + clients exist
        if packet != last_packet and connected_clients:
            try:
                await asyncio.gather(*[
                    ws.send(packet) for ws in connected_clients
                ])
                last_packet = packet
            except Exception as e:
                print("Joystick Send error:", e)

        await asyncio.sleep(SEND_RATE)


# ---------------------- Main ----------------------
async def main():
    print(f"WS Server running on: ws://{SERVER_HOST}:{SERVER_PORT}/")

    server = await websockets.serve(handler, SERVER_HOST, SERVER_PORT, ping_interval=None)

    # Run Server, Joystick, and Console simultaneously
    await asyncio.gather(
        server.wait_closed(),
        controller_loop(),
        console_loop()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")