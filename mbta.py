import time
import threading
from datetime import datetime, timezone
import urllib.request
import json
from notify import check_and_show_notification

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw

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

# MBTA colors
RED       = (218, 41, 28)
WHITE     = (255, 255, 255)
BG        = (0, 0, 0)
YELLOW    = (255, 220, 0)
NOW_GREEN = (0, 220, 80)
GRAY      = (40, 40, 40)
DIM       = (100, 100, 100)

API_KEY = "37ad2966559e4902af8d13a2c5c8cd8d"
STOP_ID = "place-cntsq"
ROUTE_ID = "Red"

# Direction labels: 0 = Ashmont/Braintree, 1 = Alewife
DIRECTION_LABELS = {0: "Ashmont", 1: "Alewife"}

# Shared state
trains = []
last_updated = None
is_realtime = False
lock = threading.Lock()


def fetch_predictions():
    url = (
        f"https://api-v3.mbta.com/predictions"
        f"?filter[stop]={STOP_ID}"
        f"&filter[route]={ROUTE_ID}"
        f"&sort=departure_time"
        f"&api_key={API_KEY}"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())["data"]
        now = datetime.now(timezone.utc)
        results = []
        for p in data:
            attr = p["attributes"]
            t = attr.get("departure_time") or attr.get("arrival_time")
            if not t:
                continue
            dt = datetime.fromisoformat(t)
            mins = int((dt - now).total_seconds() / 60)
            if mins < 0:
                continue
            direction = DIRECTION_LABELS.get(attr["direction_id"], "?")
            results.append({"direction": direction, "min": mins})
            if len(results) == 3:
                break
        return results, True
    except Exception:
        return None, False


def fetch_schedules():
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    url = (
        f"https://api-v3.mbta.com/schedules"
        f"?filter[stop]={STOP_ID}"
        f"&filter[route]={ROUTE_ID}"
        f"&filter[min_time]={time_str}"
        f"&sort=departure_time"
        f"&page[limit]=3"
        f"&api_key={API_KEY}"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())["data"]
        now_utc = datetime.now(timezone.utc)
        results = []
        for s in data:
            attr = s["attributes"]
            t = attr.get("departure_time") or attr.get("arrival_time")
            if not t:
                continue
            dt = datetime.fromisoformat(t)
            mins = int((dt - now_utc).total_seconds() / 60)
            if mins < 0:
                continue
            direction = DIRECTION_LABELS.get(attr["direction_id"], "?")
            results.append({"direction": direction, "min": mins})
        return results
    except Exception:
        return []


def poll_loop():
    global trains, last_updated, is_realtime
    while True:
        preds, realtime = fetch_predictions()
        with lock:
            if preds:
                trains = preds
                is_realtime = realtime
            else:
                fallback = fetch_schedules()
                trains = fallback
                is_realtime = False
            last_updated = datetime.now()
        time.sleep(30)


# Start polling in background
t = threading.Thread(target=poll_loop, daemon=True)
t.start()

# Wait for first fetch
time.sleep(2)



def format_time(min_val):
    if min_val == 0:
        return "Now"
    return f"{min_val} m"


def time_color(min_val):
    return NOW_GREEN if min_val == 0 else YELLOW


def draw_t_logo(draw, x, y):
    draw.ellipse([(x, y), (x + 7, y + 7)], fill=RED)
    draw.text((x + 2, y), "T", fill=WHITE)


def draw_frame(blink_on):
    image = Image.new("RGB", (64, 32), BG)
    draw = ImageDraw.Draw(image)

    # Header bar
    draw.rectangle([(0, 0), (63, 1)], fill=RED)
    draw_t_logo(draw, 1, 2)
    draw.text((11, 2), "Central Sq", fill=WHITE)

    # Live/schedule indicator dot
    dot_color = NOW_GREEN if (blink_on and is_realtime) else (DIM if not is_realtime else BG)
    draw.rectangle([(61, 2), (63, 4)], fill=dot_color)

    # Layout (32px total):
    # 0-1:  red bar
    # 2-9:  header
    # 10:   divider
    # 11-18: train 1 text (y=11)
    # 19:   divider
    # 20-27: train 2 text (y=20)
    # 28-31: third train hint (y=28, dim)

    with lock:
        current_trains = list(trains)

    if not current_trains:
        draw.text((2, 13), "No predictions", fill=DIM)
        return image

    # Train row 1
    t1 = current_trains[0]
    draw.text((2, 11), t1["direction"], fill=WHITE)
    t1_str = format_time(t1["min"])
    draw.text((63 - len(t1_str) * 6, 11), t1_str, fill=time_color(t1["min"]))

    # Train row 2
    if len(current_trains) > 1:
        t2 = current_trains[1]
        draw.text((2, 20), t2["direction"], fill=WHITE)
        t2_str = format_time(t2["min"])
        draw.text((63 - len(t2_str) * 6, 20), t2_str, fill=time_color(t2["min"]))

    return image


blink = True
tick = 0

while True:
    check_and_show_notification(matrix, canvas)

    image = draw_frame(blink)
    canvas.SetImage(image)
    canvas = matrix.SwapOnVSync(canvas)

    tick += 1
    if tick % 15 == 0:
        blink = not blink

    time.sleep(0.04)
