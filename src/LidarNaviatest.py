import asyncio
import websockets
import json
import contextlib
import datetime
from rplidar import RPLidar, RPLidarException

# --- CONFIGURATION ---
LIDAR_PORT = '/dev/ttyUSB0'
LIDAR_BAUD = 115200
WS_PORT = 8765

connected_clients = set()


# --- HELPER FUNCTION (THE FIX) ---
# We need this because 'next()' can raise StopIteration, which crashes asyncio executors.
def _fetch_scan_safe(iterator):
    try:
        return next(iterator)
    except StopIteration:
        raise Exception("Iterator stopped")
    except Exception as e:
        raise e


async def broadcast_callback(msg):
    """Sends the message to all connected clients"""
    if connected_clients:
        payload = json.dumps(msg)
        await asyncio.gather(
            *[client.send(payload) for client in connected_clients],
            return_exceptions=True
        )


# --- YOUR ORIGINAL FUNCTION (Restored & Patched) ---
async def lidar_loop():
    lidar = None
    try:
        print(f'[LIDAR] Abriendo {LIDAR_PORT} @ {LIDAR_BAUD}')
        lidar = RPLidar(LIDAR_PORT, baudrate=LIDAR_BAUD, timeout=3)

        # FIX 1: Clean buffer before starting
        lidar.stop()
        lidar.stop_motor()
        lidar.disconnect()
        await asyncio.sleep(1)

        lidar = RPLidar(LIDAR_PORT, baudrate=LIDAR_BAUD, timeout=3)
        lidar.start_motor()
        await asyncio.sleep(2)  # Wait for spin up

        # Try to clean input if method exists
        if hasattr(lidar, 'clean_input'):
            lidar.clean_input()

        print("[LIDAR] Motor spinning... starting scan.")

        loop = asyncio.get_running_loop()

        # FIX 2: Add max_buf_meas=8000 to prevent "Wrong body size"
        it = lidar.iter_scans(max_buf_meas=8000, min_len=5)
        seq = 0

        while True:
            # FIX 3: Use _fetch_scan_safe instead of raw 'next'
            try:
                scan = await loop.run_in_executor(None, _fetch_scan_safe, it)
            except Exception as e:
                print(f"[LIDAR] Glitch: {e} -> Resyncing...")
                # Rapid recovery: Clean buffer and recreate iterator
                try:
                    lidar.clean_input()
                except:
                    pass
                it = lidar.iter_scans(max_buf_meas=8000, min_len=5)
                continue

            seq += 1

            # Formato: [[ángulo, distancia, calidad], ...]
            # Filter valid points (dist > 0) to save bandwidth
            pts = [[a, d, q] for (q, a, d) in scan if d > 0]

            msg = {
                "type": "scan",
                "seq": seq,
                "ts": datetime.datetime.now().isoformat(),
                "points": pts
            }

            # Broadcast
            await broadcast_callback(msg)

    except (RPLidarException, OSError) as e:
        print(f'[LIDAR] ⚠️ CRITICAL: {e}')
    except asyncio.CancelledError:
        pass
    finally:
        if lidar:
            with contextlib.suppress(Exception):
                lidar.stop()
                lidar.stop_motor()
                lidar.disconnect()
        print('[LIDAR] loop terminado')


# --- BOILERPLATE TO RUN IT ---
async def ws_handler(websocket):
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)


async def main():
    # Start LiDAR Loop
    asyncio.create_task(lidar_loop())

    # Start Server
    print(f"[SERVER] Running on ws://0.0.0.0:{WS_PORT}")
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping...")
