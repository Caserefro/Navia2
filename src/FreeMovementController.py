import asyncio
import websockets
import pygame
import time
import math

WS_URL = "ws://192.168.1.126:8765"

DEADZONE = 0.15
ROTATION_STEP = 0.1
ROTATION_DECAY = 0.02
SEND_RATE = 0.02


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

    while True:
        pygame.event.pump()

        # Left stick
        lx = deadzone(js.get_axis(0))
        ly = -deadzone(js.get_axis(1))   # invert Y
        nx, ny = normalize_vector(lx, ly)
        m_msg = f"M,{nx:.2f},{ny:.2f}"

        # Rotation
        if js.get_button(5):  # R
            rotation += ROTATION_STEP
        if js.get_button(4):  # L
            rotation -= ROTATION_STEP

        # Decay toward zero
        if rotation > 0:
            rotation -= ROTATION_DECAY
        elif rotation < 0:
            rotation += ROTATION_DECAY

        rotation = max(-1.0, min(1.0, rotation))
        r_msg = f"R,{rotation:.2f}"

        try:
            # Send only changes
            if m_msg != last_m_msg:
                await ws.send(m_msg)
                last_m_msg = m_msg

            if r_msg != last_r_msg:
                await ws.send(r_msg)
                last_r_msg = r_msg

        except websockets.exceptions.ConnectionClosed:
            print("⚠️  WS disconnected while sending.")
            return  # break to reconnect

        except Exception as e:
            print(f"⚠️  Send error: {e}")
            return

        await asyncio.sleep(SEND_RATE)


async def main():
    while True:
        try:
            print(f"Connecting to {WS_URL} ...")
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
                print("Connected! 🎉")
                await send_controller(ws)

        except Exception as e:
            print(f"❌ Connection error: {e}")
            print("🔄 Reconnecting in 2 seconds...")
            await asyncio.sleep(2)


asyncio.run(main())
