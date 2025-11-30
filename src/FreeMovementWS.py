import asyncio

import serial_asyncio
import websockets

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

connected_clients = set()
serial_writer = None


async def serial_reader():
    global serial_writer
    try:
        reader, serial_writer = await serial_asyncio.open_serial_connection(
            url=SERIAL_PORT,
            baudrate=BAUD_RATE
        )
        print(f"Serial.open({SERIAL_PORT}, {BAUD_RATE})")
    except Exception as e:
        print(f"FATAL: Could not open serial port: {e}")
        return

    while True:
        try:
            line = await reader.readline()
            if not line:
                continue

            # Decode with error replacement to prevent crashing on garbage bytes
            text = line.decode(errors="replace").strip()
            print(f"[SERIAL] {text}")

            # Only attempt broadcast if there are clients
            if connected_clients:
                # return_exceptions=True prevents one bad client from crashing the loop
                await asyncio.gather(
                    *[client.send(text) for client in connected_clients],
                    return_exceptions=True
                )

        except Exception as e:
            print(f"Serial read error: {e}")
            await asyncio.sleep(1)  # Prevent CPU spam if serial fails


async def ws_handler(websocket):
    print("[WS] Client connected")
    connected_clients.add(websocket)

    try:
        async for message in websocket:
            print(f"[WS] {message}")

            if serial_writer:
                serial_writer.write((message + "\n").encode())
                # CRITICAL: Drain allows the buffer to empty, preventing lag
                await serial_writer.drain()

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        connected_clients.remove(websocket)
        print("[WS] Client disconnected")


async def main():
    # Start serial read task in background
    asyncio.create_task(serial_reader())

    # Start WebSocket server
    # ping_interval=None disables the SERVER pinging the CLIENT.
    # Let the Client manage the pings to reduce network chatter.
    async with websockets.serve(
            ws_handler,
            "0.0.0.0",
            8765,
            ping_interval=None,  # Disable server pings
            ping_timeout=None  # Disable ping timeout
    ):
        print("WebSocket server started on ws://0.0.0.0:8765")
        # Keep the server running forever
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopping...")
