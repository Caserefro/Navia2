import asyncio
import math

import pygame
import websockets

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

DEADZONE = 0.15
ROTATION_STEP = 0.05
ROTATION_DECAY = 0.02
SEND_RATE = 0.02  # 100 ms
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
    print("ESP32 connected:", ws.remote_address)
    connected_clients.add(ws)

    try:
        async for msg in ws:
            print(f"[ESP32 → PC] {msg}")
    except websockets.ConnectionClosed:
        print("ESP32 disconnected")
    finally:
        connected_clients.remove(ws)


# ---------------------- Controller Loop ----------------------
async def controller_loop():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller found!")
        return

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

        # Rotation using shoulder buttons
        if js.get_button(9):  # Right shoulder
            th += ROTATION_STEP
        if js.get_button(10):  # Left shoulder
            th -= ROTATION_STEP

        # Decay
        if th > 0:
            th -= ROTATION_DECAY
        elif th < 0:
            th += ROTATION_DECAY

        # Snap to zero to prevent oscillation
        if abs(th) < ROTATION_DECAY:
            th = 0.0

        # Limit range
        th = max(-1.0, min(1.0, th))

        # *** Final unified packet ***
        packet = f"{-x_s:.2f},{y_s:.2f},{th:.2f}"

        # Send only if changed + at least one ESP32 connected
        if packet != last_packet and connected_clients:
            try:
                await asyncio.gather(*[
                    ws.send(packet) for ws in connected_clients
                ])
                last_packet = packet
            except Exception as e:
                print("Send error:", e)

        await asyncio.sleep(SEND_RATE)


# ---------------------- Main ----------------------
async def main():
    print(f"WS Server: ws://{SERVER_HOST}:{SERVER_PORT}/")
    server = await websockets.serve(handler, SERVER_HOST, SERVER_PORT, ping_interval=20, ping_timeout=20)

    await asyncio.gather(
        server.wait_closed(),
        controller_loop()
    )


asyncio.run(main())
