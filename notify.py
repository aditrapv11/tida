"""
Shared Claude notification overlay for all Tidabit display apps.

Usage:
    from notify import check_and_show_notification
    # In your main loop:
    check_and_show_notification(matrix, canvas)
"""
import os
import math
import time
import random
from PIL import Image, ImageDraw

NOTIFY_FLAG      = "/tmp/claude_notify"
NOTIFY_DURATION  = 5.0   # seconds to show
NOTIFY_FRESHNESS = 8.0   # only trigger if flag written within this many seconds
NOTIFY_COOLDOWN  = 10.0  # minimum gap between notifications

_start_time = time.time()
_last_notify_time = 0.0

# Classic space invader sprite (7 wide x 5 tall)
INVADER = [
    "0111110",
    "1111111",
    "1010101",
    "1111111",
    "0100010",
]
SPRITE_W = 7
SPRITE_H = 5

# Classic arcade color palette
ARCADE_COLORS = [
    (0, 255, 0),     # green
    (0, 255, 255),   # cyan
    (255, 0, 255),   # magenta
    (255, 255, 0),   # yellow
    (255, 128, 0),   # orange
    (255, 255, 255), # white
]

SPEED = 15.0  # pixels per second


def _draw_invader(pixels, x, y, color):
    for row_i, row in enumerate(INVADER):
        for col_i, px in enumerate(row):
            if px == '1':
                px_x = int(x) + col_i
                px_y = int(y) + row_i
                if 0 <= px_x < 64 and 0 <= px_y < 32:
                    pixels[px_x, px_y] = color


def _run_animation(matrix, canvas):
    rng = random.Random(int(time.time()))

    # 15 invaders: random x, staggered y starts above screen
    invaders = []
    for i in range(15):
        x = rng.randint(0, 64 - SPRITE_W)
        y_start = -(SPRITE_H + rng.randint(0, 22))
        color = rng.choice(ARCADE_COLORS)
        invaders.append({"x": x, "y_start": y_start, "color": color})

    # Twinkling stars: fixed positions, random phase
    stars = [
        (rng.randint(0, 63), rng.randint(0, 31), rng.uniform(0, math.pi * 2))
        for _ in range(20)
    ]

    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed >= NOTIFY_DURATION:
            break

        fade = max(0.0, 1.0 - elapsed / NOTIFY_DURATION)  # 1.0 → 0.0

        image = Image.new("RGB", (64, 32), (0, 0, 0))
        pixels = image.load()
        draw = ImageDraw.Draw(image)

        # Twinkling stars
        for sx, sy, phase in stars:
            brightness = int(((math.sin(elapsed * 5 + phase) + 1) / 2) * 180 + 40)
            pixels[sx, sy] = (brightness, brightness, brightness)

        # Falling invaders
        for inv in invaders:
            y = inv["y_start"] + elapsed * SPEED
            _draw_invader(pixels, inv["x"], y, inv["color"])

        # "CLAUDE" centered, fading out
        text = "CLAUDE"
        text_w = len(text) * 6
        tx = (64 - text_w) // 2
        ty = (32 - 8) // 2
        alpha = int(255 * fade)
        draw.text((tx, ty), text, fill=(alpha, alpha, alpha))

        canvas.SetImage(image)
        matrix.SwapOnVSync(canvas)
        time.sleep(0.04)


def check_and_show_notification(matrix, canvas):
    """Show space invader shower if flag file is fresh."""
    global _last_notify_time

    if not os.path.exists(NOTIFY_FLAG):
        return

    try:
        with open(NOTIFY_FLAG) as f:
            written_at = float(f.read().strip())
    except (ValueError, OSError):
        return

    try:
        os.remove(NOTIFY_FLAG)
    except OSError:
        pass

    now = time.time()

    if written_at < _start_time:
        return
    if now - written_at > NOTIFY_FRESHNESS:
        return
    if now - _last_notify_time < NOTIFY_COOLDOWN:
        return

    _last_notify_time = now
    _run_animation(matrix, canvas)
