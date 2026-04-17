import time
import math
import random
import threading
import urllib.request
import json

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw
from notify import check_and_show_notification

# Cambridge MA 02139
LAT = 42.3736
LON = -71.1097

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

# Shared weather state
weather = {"temp": None, "feels_like": None, "rain_12h": None, "condition": "sunny"}
lock = threading.Lock()
needs_rerender = True

# Animation constants
NUM_FRAMES = 21       # frames in one loop
FPS = 7
FRAME_DT = 1.0 / FPS

# Pre-seeded particle positions (fixed, no randomness at runtime)
rng = random.Random(42)
drops  = [(rng.randint(1, 22), rng.randint(0, 31), rng.uniform(0.6, 1.0)) for _ in range(10)]
flakes = [(rng.randint(1, 22), rng.randint(0, 31), rng.uniform(0.3, 0.7)) for _ in range(8)]
star_positions = [(rng.randint(0, 22), rng.randint(0, 31), rng.uniform(0, math.pi * 2))
                  for _ in range(15)]

# ── API ──────────────────────────────────────────────────────────────────────

def fetch_weather():
    global needs_rerender
    try:
        req = urllib.request.Request(
            f"https://api.weather.gov/points/{LAT},{LON}",
            headers={"User-Agent": "tidabit/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            pts = json.loads(r.read())
        hourly_url = pts["properties"]["forecastHourly"]

        req2 = urllib.request.Request(hourly_url, headers={"User-Agent": "tidabit/1.0"})
        with urllib.request.urlopen(req2, timeout=10) as r:
            data = json.loads(r.read())

        periods = data["properties"]["periods"]
        cur = periods[0]
        temp_f = cur["temperature"]

        wind_mph = 0.0
        try:
            wind_mph = float(cur.get("windSpeed", "0 mph").split()[0])
        except ValueError:
            pass

        if temp_f <= 50 and wind_mph >= 3:
            feels = int(35.74 + 0.6215 * temp_f
                        - 35.75 * wind_mph ** 0.16
                        + 0.4275 * temp_f * wind_mph ** 0.16)
        elif temp_f >= 80:
            rh = cur.get("relativeHumidity", {}).get("value", 50) or 50
            feels = int(-42.379 + 2.04901523 * temp_f + 10.14333127 * rh
                        - 0.22475541 * temp_f * rh - 0.00683783 * temp_f ** 2
                        - 0.05481717 * rh ** 2 + 0.00122874 * temp_f ** 2 * rh
                        + 0.00085282 * temp_f * rh ** 2
                        - 0.00000199 * temp_f ** 2 * rh ** 2)
        else:
            feels = temp_f

        rain_12h = max(
            (p.get("probabilityOfPrecipitation", {}).get("value") or 0)
            for p in periods[:12])

        forecast = cur.get("shortForecast", "").lower()
        if any(w in forecast for w in ["thunder", "storm"]):
            condition = "stormy"
        elif any(w in forecast for w in ["snow", "blizzard", "flurr"]):
            condition = "snowy"
        elif any(w in forecast for w in ["rain", "shower", "drizzle"]):
            condition = "rainy"
        elif any(w in forecast for w in ["cloud", "overcast", "fog"]):
            condition = "cloudy"
        else:
            condition = "sunny"

        with lock:
            weather["temp"] = int(temp_f)
            weather["feels_like"] = int(feels)
            weather["rain_12h"] = int(rain_12h)
            weather["condition"] = condition
        needs_rerender = True

    except Exception:
        pass


def poll_loop():
    while True:
        fetch_weather()
        time.sleep(300)


threading.Thread(target=poll_loop, daemon=True).start()
time.sleep(2)

# ── Icon renderers (called at pre-render time only) ───────────────────────────

def render_sunny(draw, i):
    draw.rectangle([(0, 0), (23, 31)], fill=(30, 80, 180))
    cx, cy, r = 12, 16, 6
    angle_offset = i / NUM_FRAMES * 2 * math.pi
    for k in range(6):
        a = angle_offset + k * math.pi / 3
        x1 = cx + math.cos(a) * (r + 1)
        y1 = cy + math.sin(a) * (r + 1)
        x2 = cx + math.cos(a) * (r + 4)
        y2 = cy + math.sin(a) * (r + 4)
        draw.line([(x1, y1), (x2, y2)], fill=(255, 230, 0))
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(255, 220, 0))


def render_cloud_shape(draw, ox, oy, fill):
    draw.ellipse([(ox+2, oy+4), (ox+14, oy+14)], fill=fill)
    draw.ellipse([(ox+5, oy+1), (ox+15, oy+11)], fill=fill)
    draw.ellipse([(ox+10, oy+4), (ox+20, oy+14)], fill=fill)
    draw.rectangle([(ox+4, oy+8), (ox+18, oy+14)], fill=fill)


def render_cloudy(draw, i):
    draw.rectangle([(0, 0), (23, 31)], fill=(60, 70, 90))
    ox = int(math.sin(i / NUM_FRAMES * 2 * math.pi) * 2)
    render_cloud_shape(draw, ox, 10, (200, 200, 210))


def render_rainy(draw, i):
    draw.rectangle([(0, 0), (23, 31)], fill=(40, 50, 70))
    render_cloud_shape(draw, 0, 8, (160, 160, 180))
    pixels_per_frame = FRAME_DT * 20
    for dx, dy, speed in drops:
        y = int((dy + i * pixels_per_frame * speed) % 32)
        if y < 31:
            draw.line([(dx, y), (dx, y + 2)], fill=(100, 160, 255))


def render_stormy(draw, i):
    draw.rectangle([(0, 0), (23, 31)], fill=(20, 20, 35))
    render_cloud_shape(draw, 0, 6, (100, 100, 120))
    pixels_per_frame = FRAME_DT * 25
    for dx, dy, speed in drops:
        y = int((dy + i * pixels_per_frame * speed) % 32)
        if y < 31:
            draw.line([(dx, y), (dx, y + 2)], fill=(80, 120, 200))
    if i % 7 == 0:
        draw.polygon([(12, 14), (9, 21), (12, 21), (9, 28)], fill=(255, 255, 100))


def render_snowy(draw, i):
    draw.rectangle([(0, 0), (23, 31)], fill=(20, 20, 50))
    render_cloud_shape(draw, 0, 8, (180, 180, 200))
    pixels_per_frame = FRAME_DT * 8
    for fx, fy, speed in flakes:
        y = int((fy + i * pixels_per_frame * speed) % 32)
        x = int(fx + math.sin(i / NUM_FRAMES * 2 * math.pi + fy) * 2)
        if 0 <= x < 24 and y < 32:
            draw.point([(x, y)], fill=(200, 220, 255))


# ── Pre-render all frames ─────────────────────────────────────────────────────

prerendered = []


def build_frames():
    global prerendered
    with lock:
        temp = weather["temp"]
        feels = weather["feels_like"]
        rain = weather["rain_12h"]
        condition = weather["condition"]

    frames = []
    for i in range(NUM_FRAMES):
        image = Image.new("RGB", (64, 32), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Animated icon — left 24px
        if condition == "sunny":
            render_sunny(draw, i)
        elif condition == "cloudy":
            render_cloudy(draw, i)
        elif condition == "rainy":
            render_rainy(draw, i)
        elif condition == "stormy":
            render_stormy(draw, i)
        elif condition == "snowy":
            render_snowy(draw, i)

        # Divider
        draw.line([(24, 0), (24, 31)], fill=(50, 50, 50))

        # Right panel — x=26..63 (38px wide, ~6px/char)
        if temp is not None:
            draw.text((26, 2),  f"{temp}°",    fill=(255, 255, 255))
            draw.text((26, 13), f"FL{feels}°", fill=(80, 80, 80))
            draw.polygon([(26, 24), (28, 21), (30, 24), (28, 27)], fill=(80, 130, 220))
            draw.text((32, 22), f"{rain}%",    fill=(80, 140, 220))
        else:
            draw.text((27, 12), "...", fill=(100, 100, 100))

        frames.append(image)

    prerendered = frames


# ── Main loop ─────────────────────────────────────────────────────────────────

build_frames()

frame_idx = 0
while True:
    check_and_show_notification(matrix, canvas)

    if needs_rerender:
        build_frames()
        needs_rerender = False

    canvas.SetImage(prerendered[frame_idx % NUM_FRAMES])
    canvas = matrix.SwapOnVSync(canvas)

    frame_idx += 1
    time.sleep(FRAME_DT)
