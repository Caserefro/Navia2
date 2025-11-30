import asyncio
import serial_asyncio
import websockets

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

connected_clients = set()
serial_writer = None

async def serial_reader():
    global serial_writer
    reader, serial_writer = await serial_asyncio.open_serial_connection(
        url=SERIAL_PORT,
        baudrate=BAUD_RATE
    )

    print(f"Serial.open({SERIAL_PORT}, {BAUD_RATE})")

    while True:
        try:
            line = await reader.readline()
            if not line:
                continue
            text = line.decode(errors="ignore").strip()
            print(f"[SERIAL] {text}")

            # Broadcast to all WebSocket clients
            await asyncio.gather(*[
                client.send(text)
                for client in connected_clients
            ])
        except Exception as e:
            print("Serial read error:", e)

async def ws_handler(websocket):
    print("[WS] Client connected")
    connected_clients.add(websocket)

    try:
        async for message in websocket:
            print(f"[WS] {message}")

            # Forward WS message to Serial
            if serial_writer:
                serial_writer.write((message + "\n").encode())

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        print("[WS] Client disconnected")

async def main():
    # Start serial read task
    asyncio.create_task(serial_reader())

    # Start WebSocket server
    server = await websockets.serve(ws_handler, "0.0.0.0", 8765)
    print("WebSocket server started on ws://0.0.0.0:8765")

    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
