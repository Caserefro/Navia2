import asyncio
import websockets
import json
from rplidar import RPLidar, RPLidarException

# --- CONFIGURATION ---
LIDAR_PORT = '/dev/ttyUSB0'
LIDAR_BAUD = 115200
WS_PORT = 8765

connected_clients = set()
lidar_instance = None  # Global reference for safe cleanup


async def lidar_reader():
    """
    Connects to the RPLidar, reads full scans, and broadcasts them.
    Runs the blocking 'next(iterator)' in a separate thread executor.
    """
    global lidar_instance
    print(f"[LIDAR] Connecting to {LIDAR_PORT}...")

    try:
        lidar_instance = RPLidar(LIDAR_PORT, baudrate=LIDAR_BAUD)

        # Helper to stop things if they were left running
        lidar_instance.stop()
        lidar_instance.stop_motor()
        await asyncio.sleep(1)  # Give it a breath

        lidar_instance.start_motor()

        # Get the iterator. This is NOT a list, it's a generator.
        # scan_generator yields lists of [quality, angle, distance]
        scan_generator = lidar_instance.iter_scans()

        loop = asyncio.get_running_loop()

        print("[LIDAR] Scanning started.")

        while True:
            try:
                # CRITICAL: next(scan_generator) is blocking! 
                # We must run it in an executor to keep the WebSocket alive.
                scan = await loop.run_in_executor(None, next, scan_generator)

                # 'scan' format is usually: [(quality, angle, distance), ...]
                # Let's clean it up for JSON (reduce data size if needed)
                # We simply convert tuples to lists
                points = [[angle, dist] for (qual, angle, dist) in scan]

                # Create the payload
                data = {
                    "type": "scan",
                    "count": len(points),
                    "points": points
                }

                json_data = json.dumps(data)

                # Broadcast to all connected clients
                if connected_clients:
                    await asyncio.gather(
                        *[client.send(json_data) for client in connected_clients],
                        return_exceptions=True
                    )

            except RPLidarException as e:
                print(f"[LIDAR] Protocol error: {e}. Retrying...")
                lidar_instance.stop()
                await asyncio.sleep(1)
                lidar_instance.start_motor()

    except Exception as e:
        print(f"[LIDAR] Fatal Error: {e}")
    finally:
        print("[LIDAR] Stopping...")
        if lidar_instance:
            lidar_instance.stop()
            lidar_instance.stop_motor()
            lidar_instance.disconnect()


async def ws_handler(websocket):
    print(f"[WS] Client connected: {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            # Handle incoming messages from client (optional)
            # You usually don't write raw bytes to the Lidar while it is scanning
            print(f"[WS] Received: {message}")

            if message == "stop":
                print("Command received: STOP")
                # Add logic here if you want to control the motor via WS

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        print("[WS] Client disconnected")


async def main():
    # Start the LiDAR reader as a background task
    asyncio.create_task(lidar_reader())

    # Start the WebSocket server
    print(f"[SERVER] Starting WebSocket on 0.0.0.0:{WS_PORT}")
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
        await asyncio.get_running_loop().create_future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopping by user request.")