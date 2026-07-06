#!/usr/bin/env python3
"""
sentry.py — HAL 9000 nighttime mode. Three red pulsing eyes drifting left.
"""
import math
import time
from PIL import Image

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    from notify import check_and_show_notification
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
    def check_and_show_notification(m, c): pass


def _get_brightness():
    try:
        return int(open('/tmp/tidabit_brightness').read().strip())
    except:
        return 80


# Three eyes at 24px spacing (2px gap between each), all at y=16.
# Rendered on a wide canvas; scroll is a per-frame crop — no per-frame pixel work.
_WIDE      = 400
_EYE_CX    = [200, 218, 236]   # centers in wide canvas (18px spacing, slight overlap)
_EYE_CY    = 16
_EYE_R     = 11                # outer glow radius


def _make_wide_eyes():
    img = Image.new("RGB", (_WIDE, 32), (0, 0, 0))
    for cx in _EYE_CX:
        x0, x1 = max(0, cx - _EYE_R - 1), min(_WIDE, cx + _EYE_R + 2)
        for y in range(32):
            for x in range(x0, x1):
                r = math.sqrt((x - cx) ** 2 + (y - _EYE_CY) ** 2)
                if r <= 2:
                    img.putpixel((x, y), (255, 0, 0))
                elif r <= 5:
                    img.putpixel((x, y), (200, 0, 0))
                elif r <= 8:
                    img.putpixel((x, y), (120, 0, 0))
                elif r <= _EYE_R:
                    fade = 1 - (r - 8) / (_EYE_R - 8)
                    img.putpixel((x, y), (int(80 * fade), 0, 0))
    return img


_WIDE_EYES = _make_wide_eyes()

# group_x = apparent display x of the leftmost eye center (_EYE_CX[0])
# 75  → eye A just off right edge
# -60 → eye C just off left edge  (248-200=48 offset, -12-48=-60)
_GX_START  = 75
_GX_END    = -48
_GX_RANGE  = _GX_START - _GX_END   # 123 px total travel
_SCROLL_T  = 25.0                   # seconds per full pass (≈5.4 px/s)


def make_frame(pulse, group_x):
    factor = 0.06 + pulse * 0.10    # 6–16% brightness, very dim
    crop_x = int(_EYE_CX[0] - group_x)
    crop_x = max(0, min(_WIDE - 64, crop_x))
    frame  = _WIDE_EYES.crop((crop_x, 0, crop_x + 64, 32))
    return frame.point(lambda p: int(p * factor))


def main():
    opts = RGBMatrixOptions()
    opts.rows = 32
    opts.cols = 64
    opts.hardware_mapping = 'adafruit-hat'
    opts.brightness = _get_brightness()
    opts.pwm_bits = 7

    matrix = RGBMatrix(options=opts)
    canvas = matrix.CreateFrameCanvas()

    t0 = time.time()
    try:
        while True:
            t       = time.time() - t0
            pulse   = (math.sin(t * 1.8) + 1) / 2      # ~3.5s glow cycle, all 3 in sync
            phase   = (t % _SCROLL_T) / _SCROLL_T        # 0→1 over 25s
            group_x = _GX_START - phase * _GX_RANGE      # 75 → -60
            canvas.SetImage(make_frame(pulse, group_x))
            canvas = matrix.SwapOnVSync(canvas)
            check_and_show_notification(matrix, canvas)
            time.sleep(0.05)
    except KeyboardInterrupt:
        matrix.Clear()


if __name__ == "__main__":
    main()
