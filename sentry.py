#!/usr/bin/env python3
"""
sentry.py — HAL 9000 nighttime mode. Deep red pulsing eye, very dim.
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


def _make_eye():
    img = Image.new("RGB", (64, 32), (0, 0, 0))
    cx, cy = 32, 16
    for y in range(32):
        for x in range(64):
            r = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if r <= 2:
                img.putpixel((x, y), (255, 0, 0))
            elif r <= 5:
                img.putpixel((x, y), (200, 0, 0))
            elif r <= 8:
                img.putpixel((x, y), (120, 0, 0))
            elif r <= 11:
                fade = 1 - (r - 8) / 3
                img.putpixel((x, y), (int(80 * fade), 0, 0))
    return img


_EYE = _make_eye()


def make_frame(pulse):
    factor = 0.06 + pulse * 0.10  # 6%–16% brightness — stays very dim
    return _EYE.point(lambda p: int(p * factor))


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
            t = time.time() - t0
            pulse = (math.sin(t * 0.4) + 1) / 2  # ~15s period, very slow
            canvas.SetImage(make_frame(pulse))
            canvas = matrix.SwapOnVSync(canvas)
            check_and_show_notification(matrix, canvas)
            time.sleep(0.05)
    except KeyboardInterrupt:
        matrix.Clear()


if __name__ == "__main__":
    main()
