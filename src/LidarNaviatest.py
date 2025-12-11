import asyncio
import websockets
import json
import contextlib
import datetime
import time
from rplidar import RPLidar, RPLidarException

# --- CONFIGURATION ---
LIDAR_PORT = '/dev/ttyUSB0'
LIDAR_BAUD = 115200
WS_PORT = 8765

connected_clients = set()


# --- HELPER: Safe Iterator Fetcher ---
def _fetch_scan_safe(iterator):
    try:
        return next(iterator)
    except StopIteration:
        raise Exception("Iterator stopped")


async def broadcast_callback(msg):
    if connected_clients:
        payload = json.dumps(msg)
        await asyncio.gather(
            *[client.send(payload) for client in connected_clients],
            return_exceptions=True
        )


# --- ROBUST LIDAR LOOP ---
async def lidar_loop():
    while True:  # OUTER LOOP: Reconnection Manager
        lidar = None
        try:
            print(f'[LIDAR] Connecting to {LIDAR_PORT}...')

            # 1. Initialize Driver
            lidar = RPLidar(LIDAR_PORT, baudrate=LIDAR_BAUD, timeout=3)

            # 2. Hard Reset (The "Magic" Sequence)
            lidar.stop()
            lidar.stop_motor()
            lidar.disconnect()

            # Use non-async sleep here to block the executor momentarily if needed,
            # but usually async sleep is better to keep WS alive.
            await asyncio.sleep(1.0)

            # Reconnect fresh
            lidar = RPLidar(LIDAR_PORT, baudrate=LIDAR_BAUD, timeout=3)
            lidar.start_motor()
            await asyncio.sleep(1.0)  # Let it spin up

            print("[LIDAR] Connected. Starting scan stream.")

            # 3. Create Iterator
            # 'max_buf_meas' is critical.
            # If your lidar is A1, 500 is usually fine.
            # If A2/A3, you might need 8000.
            # TRYING 3000 as a safe middle ground.
            iterator = lidar.iter_scans(max_buf_meas=3000, min_len=10)

            loop = asyncio.get_running_loop()
            seq = 0

            # INNER LOOP: Data Streaming
            while True:
                try:
                    # Run blocking 'next' in a thread
                    scan = await loop.run_in_executor(None, _fetch_scan_safe, iterator)

                    seq += 1
                    # Filter: Quality > 0 and Distance > 0
                    pts = [[a, d, q] for (q, a, d) in scan if d > 0]

                    msg = {
                        "type": "scan",
                        "seq": seq,
                        "ts": datetime.datetime.now().isoformat(),
                        "points": pts
                    }

                    # Fire and forget (don't await strictly)
                    asyncio.create_task(broadcast_callback(msg))

                except Exception as e:
                    # Capture the glitch and BREAK to the Outer Loop
                    print(f"[LIDAR] Stream Glitch: {e}")
                    break

        except RPLidarException as e:
            print(f"[LIDAR] Hardware Error: {e}")
        except Exception as e:
            print(f"[LIDAR] General Error: {e}")
        except asyncio.CancelledError:
            print("[LIDAR] Task Cancelled")
            break
        finally:
            # Clean up before restarting the loop
            print("[LIDAR] Resetting driver...")
            if lidar:
                try:
                    lidar.stop()
                    lidar.stop_motor()
                    lidar.disconnect()
                except:
                    pass
            await asyncio.sleep(2.0)  # Cooldown before retry


# --- SERVER BOILERPLATE ---
async def ws_handler(websocket):
    connected_clients.add(websocket)
    print(f"[WS] Client connected: {websocket.remote_address}")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print(f"[WS] Client disconnected")


async def main():
    asyncio.create_task(lidar_loop())
    print(f"[SERVER] Listening on ws://0.0.0.0:{WS_PORT}")
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass