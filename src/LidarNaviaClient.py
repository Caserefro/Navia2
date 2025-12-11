import asyncio
import websockets
import json
import pygame
import math
import threading

# --- CONFIGURATION ---
SERVER_IP = "10.215.238.142"  # Keep matching your Pi
PORT = 8765
WINDOW_SIZE = 800
MAX_DISTANCE_MM = 4000  # 4 meters radius
SCALE = (WINDOW_SIZE / 2) / MAX_DISTANCE_MM

# --- NEW HIGH-CONTRAST COLORS ---
BACKGROUND = (5, 5, 10)  # Very deep dark blue-black
GRID_COLOR = (0, 80, 180)  # Electric Blue for grid rings
POINT_COLOR = (0, 255, 220)  # Neon Cyan for standard points
DANGER_COLOR = (255, 60, 0)  # Bright Orange-Red for warnings
UI_COLOR = (200, 240, 255)  # Crisp white-blue for text and robot icon

# Global Data
latest_scan = []
lock = threading.Lock()


async def ws_listener():
    # (This function remains unchanged)
    uri = f"ws://{SERVER_IP}:{PORT}"
    print(f"Connecting to {uri}...")
    while True:
        try:
            async with websockets.connect(uri) as ws:
                print("Connected!")
                async for msg in ws:
                    data = json.loads(msg)
                    if "points" in data:
                        with lock:
                            global latest_scan
                            latest_scan = data["points"]
        except Exception as e:
            print(f"Connection error: {e}")
            await asyncio.sleep(2)


def draw_radar(screen, font):
    # 1. Fade Effect (Trails)
    fade_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE))
    fade_surface.set_alpha(35)  # Slightly faster fade for cleaner look
    fade_surface.fill(BACKGROUND)
    screen.blit(fade_surface, (0, 0))

    center = (WINDOW_SIZE // 2, WINDOW_SIZE // 2)

    # 2. Draw HUD Grid (Now using Electric Blue)
    pygame.draw.circle(screen, GRID_COLOR, center, int(1000 * SCALE), 1)
    pygame.draw.circle(screen, GRID_COLOR, center, int(2000 * SCALE), 1)
    pygame.draw.circle(screen, GRID_COLOR, center, int(3000 * SCALE), 1)
    # Crosshairs
    pygame.draw.line(screen, GRID_COLOR, (center[0] - 30, center[1]), (center[0] + 30, center[1]), 1)
    pygame.draw.line(screen, GRID_COLOR, (center[0], center[1] - 30), (center[0], center[1] + 30), 1)

    # 3. Process Points
    with lock:
        points = list(latest_scan)

    min_dist = 9999

    for point in points:
        # Handle 2 or 3 values (fallback for safety)
        if len(point) == 3:
            angle, dist, quality = point
        else:
            angle, dist = point
            quality = 40  # Default good quality

        if dist > 0:
            if dist < min_dist: min_dist = dist

            # Math: Polar to Cartesian
            rad = math.radians(angle - 90)
            x = center[0] + math.cos(rad) * (dist * SCALE)
            y = center[1] + math.sin(rad) * (dist * SCALE)

            # --- NEW COLOR LOGIC ---
            if dist < 500:  # Proximity Warning (< 50cm)
                # Hot Orange-Red, slightly larger dot
                color = DANGER_COLOR
                radius = 3
            else:
                # Standard Points: Neon Cyan
                radius = 2
                # Simple dimming for low quality points: reduce brightness by half
                if quality < 10:
                    color = (POINT_COLOR[0] // 2, POINT_COLOR[1] // 2, POINT_COLOR[2] // 2)
                else:
                    color = POINT_COLOR

            pygame.draw.circle(screen, color, (int(x), int(y)), radius)

    # 4. Robot Self (Triangle in center)
    pygame.draw.polygon(screen, UI_COLOR, [
        (center[0], center[1] - 12),
        (center[0] - 9, center[1] + 9),
        (center[0] + 9, center[1] + 9)
    ])

    # 5. UI Text
    # Main stats in bright UI color
    text = font.render(f"POINTS: {len(points)}", True, UI_COLOR)
    screen.blit(text, (20, 20))

    # Distance warning changes color dynamically
    warn_color = DANGER_COLOR if min_dist < 500 else UI_COLOR
    dist_text = font.render(f"NEAREST: {int(min_dist)}mm", True, warn_color)
    screen.blit(dist_text, (20, 45))


def main():
    # (This function remains unchanged)
    t = threading.Thread(target=lambda: asyncio.run(ws_listener()), daemon=True)
    t.start()

    pygame.init()
    # Set icon (optional, generates a small cyan square icon)
    icon = pygame.Surface((32, 32))
    icon.fill(POINT_COLOR)
    pygame.display.set_icon(icon)

    screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
    pygame.display.set_caption("NAVIA LIDAR SENSOR")
    clock = pygame.time.Clock()
    # Use a cooler, bold font if available, else fallback to monospace
    try:
        font = pygame.font.SysFont("impact", 20)
    except:
        font = pygame.font.SysFont("monospace", 18, bold=True)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        draw_radar(screen, font)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()