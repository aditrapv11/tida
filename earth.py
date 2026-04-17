import time
import math
import random
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
from PIL import Image
from notify import check_and_show_notification

options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
try:
    options.brightness = int(open("/tmp/tidabit_brightness").read().strip())
except:
    options.brightness = 80
options.pwm_bits = 7
options.hardware_mapping = 'adafruit-hat'

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# Simplified world map texture (64 wide x 32 tall, equirectangular)
# 1 = land, 0 = ocean
WORLD_W = 64
WORLD_H = 32
world_map = [
    "0000000000000000000000000000000000000000000000000000000000000000",
    "0000000000000000000000000000000000000000000000000000000000000000",
    "0000000000000000000000000000000000000000000000000000000000000000",
    "0000000011111000000000011100000000000000000001111111110000000000",
    "0000000111111100000001111110000000000000001111111111111000000000",
    "0000001111111110000011111111000000000000011111111111111100000000",
    "0000001111111111001111111111100000000000111111111111111110000000",
    "0000000111111111111111111111100000000001111111111111111110000000",
    "0000000011111111111111111110000000000011111111111111111100000000",
    "0000000001111111111111111100000000000011111111111111111000000000",
    "0000000000111111111111110000000000000001111111111111100000000000",
    "0000000000011111111111100000000000000011111111111110000000000000",
    "0000000000001111111111000000000000000011111111111100000000000000",
    "0000000000000111111110000000000000000001111111111000000000000000",
    "0000000000000011111100000000000000000000111111110000000000000000",
    "0000000000000001111000000000000000000000011111100000000000000000",
    "0000000000000000111000000000000000000000001111000000000000000000",
    "0000000000000000011000000000010000000000001110000000000000000000",
    "0000000000000000011000000000110000000001001100000000000000000000",
    "0000000000000000001100000000110000000001111000000000000000000000",
    "0000000000000000001110000000110000000000111000000001100000000000",
    "0000000000000000001111000000110000000000010000001111110000000000",
    "0000000000000000000111100000010000000000000000001111100000000000",
    "0000000000000000000011110000000000000000000000000111000000000000",
    "0000000000000000000001100000000000000000000000000010000000000000",
    "0000000000000000000000000000000000000000000000000000000000000000",
    "0000000000000000000000000000000000000000000000000000000000000000",
    "0000000000000000000000000000000000000000000000000000000000000000",
    "0000000000000000000000000000000000000000000000000000000000000000",
    "0000000000000000000000000000000000000000000000000000000000000000",
    "0000000000000000000000000000000000000000000000000000000000000000",
    "0000000000000000000000000000000000000000000000000000000000000000",
]

# Random stars
random.seed(42)
stars = [(random.randint(0, 63), random.randint(0, 31)) for _ in range(20)]

RADIUS = 14
CX = 32
CY = 16

# ISS orbit
ISS_ORBIT_R = RADIUS + 4
ISS_INCLINATION = math.radians(40)  # orbital tilt

earth_angle = 0.0
iss_angle = 0.0

while True:
    image = Image.new("RGB", (64, 32), (0, 0, 0))
    pixels = image.load()

    # Stars
    for sx, sy in stars:
        pixels[sx, sy] = (180, 180, 180)

    # ISS 3D position (orbit in tilted plane)
    iss_x = ISS_ORBIT_R * math.cos(iss_angle)
    iss_y = ISS_ORBIT_R * math.sin(iss_angle) * math.sin(ISS_INCLINATION)
    iss_z = ISS_ORBIT_R * math.sin(iss_angle) * math.cos(ISS_INCLINATION)

    iss_px = int(CX + iss_x)
    iss_py = int(CY + iss_y)
    iss_in_front = iss_z >= 0  # positive z = in front of Earth

    # Draw ISS behind Earth first (if behind)
    if not iss_in_front:
        for dx, dy, color in [
            (-2, 0, (80, 80, 60)),   # left solar panel (dimmed when behind)
            (-1, 0, (80, 80, 60)),
            (0, 0, (80, 80, 60)),    # body
            (1, 0, (80, 80, 60)),
            (2, 0, (80, 80, 60)),    # right solar panel
        ]:
            ix, iy = iss_px + dx, iss_py + dy
            if 0 <= ix < 64 and 0 <= iy < 32:
                pixels[ix, iy] = color

    # Draw Earth sphere
    for py in range(32):
        for px in range(64):
            dx = px - CX
            dy = py - CY
            dist_sq = dx * dx + dy * dy

            if dist_sq <= RADIUS * RADIUS:
                nx = dx / RADIUS
                ny = dy / RADIUS
                nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))

                lat = math.asin(-ny)
                lon = math.atan2(nx, nz)

                tx = int(((lon / (2 * math.pi) + 0.5 + earth_angle) % 1.0) * WORLD_W)
                ty = int((0.5 - lat / math.pi) * WORLD_H)
                tx = max(0, min(WORLD_W - 1, tx))
                ty = max(0, min(WORLD_H - 1, ty))

                light = 0.3 + 0.7 * nz

                if world_map[ty][tx] == '1':
                    pixels[px, py] = (int(20 * light), int(160 * light), int(40 * light))
                else:
                    pixels[px, py] = (0, int(60 * light), int(220 * light))

    # Draw ISS in front of Earth
    if iss_in_front:
        for dx, dy, color in [
            (-2, 0, (200, 200, 160)),  # left solar panel
            (-1, 0, (220, 220, 180)),
            (0, 0, (255, 255, 255)),   # body
            (1, 0, (220, 220, 180)),
            (2, 0, (200, 200, 160)),   # right solar panel
        ]:
            ix, iy = iss_px + dx, iss_py + dy
            if 0 <= ix < 64 and 0 <= iy < 32:
                pixels[ix, iy] = color

    check_and_show_notification(matrix, canvas)

    canvas.SetImage(image)
    canvas = matrix.SwapOnVSync(canvas)

    earth_angle += 0.004
    if earth_angle >= 1.0:
        earth_angle -= 1.0

    iss_angle += 0.06  # ISS orbits faster than Earth rotates
    if iss_angle >= 2 * math.pi:
        iss_angle -= 2 * math.pi

    time.sleep(0.04)
