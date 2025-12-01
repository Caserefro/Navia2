import asyncio
import websockets
import pygame
import math

WS_URL = "ws://192.168.1.126:8765"

DEADZONE = 0.15
ROTATION_STEP = 0.1
ROTATION_DECAY = 0.02
SEND_RATE = 0.02
SMOOTH_ALPHA = 0.3   # smoothing factor

def deadzone(x):
    return 0.0 if abs(x) < DEADZONE else x

def normalize_vector(x, y):
    mag = math.sqrt(x * x + y * y)
    if mag > 1.0:
        return x / mag, y / mag
    return x, y

async def send_controller(ws):
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller connected!")
        return

    js = pygame.joystick.Joystick(0)
    js.init()
    print(f"Using controller: {js.get_name()}")

    last_m_msg = ""
    last_r_msg = ""

    rotation = 0.0
    smooth_x = 0.0
    smooth_y = 0.0

    while True:
        pygame.event.pump()
        # Left stick (raw)
        lx = deadzone(js.get_axis(0))
        ly = -deadzone(js.get_axis(1))

        # Normalize
        nx, ny = normalize_vector(lx, ly)

        # Smooth
        smooth_x = SMOOTH_ALPHA * nx + (1 - SMOOTH_ALPHA) * smooth_x
        smooth_y = SMOOTH_ALPHA * ny + (1 - SMOOTH_ALPHA) * smooth_y

        m_msg = f"M,{smooth_x:.2f},{smooth_y:.2f}"

        # Rotation — updated later once we know button indices
        if js.get_button(9):  # change these after debugging
            rotation += ROTATION_STEP
        if js.get_button(10):  # change these after debugging
            rotation -= ROTATION_STEP

        # Decay
        if rotation > 0:
            rotation -= ROTATION_DECAY
        elif rotation < 0:
            rotation += ROTATION_DECAY

        rotation = max(-1.0, min(1.0, rotation))
        r_msg = f"R,{rotation:.2f}"

        try:
            if m_msg != last_m_msg:
                await ws.send(m_msg)
                last_m_msg = m_msg

            if r_msg != last_r_msg:
                await ws.send(r_msg)
                last_r_msg = r_msg

        except websockets.exceptions.ConnectionClosed:
            print("WS disconnected")
            return
        except Exception as e:
            print("Send error:", e)
            return

        await asyncio.sleep(SEND_RATE)

async def main():
    while True:
        try:
            async with websockets.connect(
                WS_URL, ping_interval=None, ping_timeout=None
            ) as ws:
                print("Connected")
                await send_controller(ws)
        except Exception as e:
            print("Reconnect:", e)

asyncio.run(main())
