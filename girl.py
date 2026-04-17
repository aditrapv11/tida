#!/usr/bin/env python3
"""
girl.py — Pixel art girl, Boston skyline background.
Blue eyes scan left/right every 3 s. Blue/white striped shirt. Brown hair.
"""
import time
from PIL import Image, ImageDraw

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    from notify import check_and_show_notification
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
    def check_and_show_notification(m, c): pass

SKIN       = (255, 195, 153)
HAIR       = (101, 55, 0)
BLUE_SHIRT = (20, 80, 200)
WHITE      = (255, 255, 255)
MOUTH      = (190, 80, 80)
NECK       = (240, 180, 140)
EYE_W      = (230, 230, 230)
EYE_BLUE   = (60, 140, 230)
PUPIL      = (15, 15, 15)
SKY        = (10, 15, 40)
WIN        = (200, 190, 120)
ANTENNA    = (100, 100, 125)


def draw_skyline(img, d):
    d.rectangle([0, 0, 63, 31], fill=SKY)

    buildings = [
        # left side
        (0,  3,  22, (35, 40, 55)),
        (4,  7,  18, (45, 50, 70)),
        (8,  11, 14, (40, 60, 95)),   # Hancock — blue glass
        (12, 15, 21, (35, 40, 55)),
        (16, 21, 24, (40, 45, 60)),
        # right side
        (42, 46, 24, (40, 45, 60)),
        (47, 51,  9, (45, 50, 70)),   # Prudential
        (52, 55, 18, (35, 40, 55)),
        (56, 59, 21, (45, 50, 70)),
        (60, 63, 25, (30, 35, 50)),
    ]

    for x0, x1, top_y, color in buildings:
        d.rectangle([x0, top_y, x1, 31], fill=color)
        for wy in range(top_y + 2, 30, 3):
            for wx in range(x0 + 1, x1, 2):
                if (wx * 3 + wy * 7) % 11 < 7:
                    img.putpixel((wx, wy), WIN)

    # Prudential antenna
    for ay in range(6, 9):
        img.putpixel((49, ay), ANTENNA)

    # Hancock antenna
    img.putpixel((9, 13), ANTENNA)
    img.putpixel((9, 12), ANTENNA)


def draw_girl(img, d, look_right):
    # Hair
    d.rectangle([24, 0, 40, 4], fill=HAIR)        # top
    d.rectangle([24, 5, 26, 20], fill=HAIR)        # left side — long
    d.rectangle([38, 5, 40, 20], fill=HAIR)        # right side — long
    d.rectangle([23, 10, 24, 20], fill=HAIR)       # left wisp
    d.rectangle([40, 10, 41, 20], fill=HAIR)       # right wisp

    # Face
    d.rectangle([27, 3, 37, 13], fill=SKIN)

    # Eyes — white base, blue iris, dark pupil
    d.rectangle([27, 6, 30, 8], fill=EYE_W)
    d.rectangle([32, 6, 35, 8], fill=EYE_W)

    if look_right:
        d.rectangle([29, 6, 30, 8], fill=EYE_BLUE)
        d.rectangle([34, 6, 35, 8], fill=EYE_BLUE)
        img.putpixel((30, 7), PUPIL)
        img.putpixel((35, 7), PUPIL)
    else:
        d.rectangle([27, 6, 28, 8], fill=EYE_BLUE)
        d.rectangle([32, 6, 33, 8], fill=EYE_BLUE)
        img.putpixel((27, 7), PUPIL)
        img.putpixel((32, 7), PUPIL)

    # Nose
    img.putpixel((32, 10), (210, 150, 110))

    # Mouth
    d.line([(29, 12), (30, 13), (34, 13), (35, 12)], fill=MOUTH)

    # Neck
    d.rectangle([30, 14, 34, 16], fill=NECK)

    # Shirt: blue/white horizontal stripes
    shirt_x0, shirt_x1 = 23, 41
    colors = [BLUE_SHIRT, WHITE]
    y, i = 17, 0
    while y <= 31:
        d.rectangle([shirt_x0, y, shirt_x1, min(y + 1, 31)], fill=colors[i % 2])
        y += 2
        i += 1


def make_frame(look_right):
    img = Image.new("RGB", (64, 32), SKY)
    d = ImageDraw.Draw(img)
    draw_skyline(img, d)
    draw_girl(img, d, look_right)
    return img


def main():
    opts = RGBMatrixOptions()
    opts.rows = 32
    opts.cols = 64
    opts.hardware_mapping = 'adafruit-hat'
    try:
        opts.brightness = int(open("/tmp/tidabit_brightness").read().strip())
    except:
        opts.brightness = 80
    opts.pwm_bits = 7

    matrix = RGBMatrix(options=opts)
    canvas = matrix.CreateFrameCanvas()

    look_right = False
    last_switch = time.time()

    try:
        while True:
            now = time.time()
            if now - last_switch >= 3.0:
                look_right = not look_right
                last_switch = now

            canvas.SetImage(make_frame(look_right))
            canvas = matrix.SwapOnVSync(canvas)
            check_and_show_notification(matrix, canvas)
            time.sleep(0.05)
    except KeyboardInterrupt:
        matrix.Clear()


if __name__ == "__main__":
    main()
