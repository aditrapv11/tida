import time
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw
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

text = "Hello World"
text_width = len(text) * 6  # ~6px per character
total_width = 64 + text_width

x = 64  # start off the right edge

while True:
    check_and_show_notification(matrix, canvas)

    image = Image.new("RGB", (64, 32))
    draw = ImageDraw.Draw(image)
    draw.text((x, 12), text, fill=(255, 100, 0))
    canvas.SetImage(image)
    canvas = matrix.SwapOnVSync(canvas)

    x -= 1
    if x < -text_width:
        x = 64  # loop back

    time.sleep(0.03)
