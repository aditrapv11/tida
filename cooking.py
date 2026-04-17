#!/usr/bin/env python3
"""
cooking.py — Recipe helper with per-step timer.
Left 47px: recipe name, step, scrolling step ingredients.
Right 16px: MM/SS countdown (scale-2 pixel font).
State: /tmp/cooking_state.json — managed by controller.py + auto-advanced here.
"""
import json
import time
from PIL import Image, ImageDraw

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    from notify import check_and_show_notification
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
    def check_and_show_notification(m, c): pass

STATE_FILE = '/tmp/cooking_state.json'
CONTENT_W  = 47
DIVIDER_X  = 47
TIMER_X    = 48

RECIPES = [
    {
        'name': 'CARBONARA',
        'steps': [
            {'desc': 'Boil water',    'ingredients': ['4qt water', 'salt'],                              'time': 600},
            {'desc': 'Cook pasta',    'ingredients': ['400g spaghetti'],                                 'time': 480},
            {'desc': 'Fry guanciale', 'ingredients': ['150g guanciale'],                                 'time': 300},
            {'desc': 'Make sauce',    'ingredients': ['4 egg yolks', '100g pecorino', 'black pepper'],   'time': None},
            {'desc': 'Combine',       'ingredients': ['pasta water', 'pasta', 'guanciale', 'sauce'],      'time': 120},
        ]
    },
    {
        'name': 'STIR FRY',
        'steps': [
            {'desc': 'Prep vegs',     'ingredients': ['bell pepper', 'broccoli', '2 garlic', 'carrot'],  'time': None},
            {'desc': 'Cook chicken',  'ingredients': ['500g chicken', '2T soy sauce', '1T sesame oil'],  'time': 420},
            {'desc': 'Fry veg',       'ingredients': ['vegs', '2T oil', 'ginger'],                       'time': 300},
            {'desc': 'Add sauce',     'ingredients': ['3T soy sauce', '1T oyster sauce', '1T cornstarch'], 'time': 180},
        ]
    },
    {
        'name': 'COOKIES',
        'steps': [
            {'desc': 'Preheat oven',  'ingredients': [],                                                  'time': 600},
            {'desc': 'Cream butter',  'ingredients': ['225g butter', '200g sugar', '2 eggs', '2t vanilla'], 'time': None},
            {'desc': 'Mix dry',       'ingredients': ['280g flour', '1t baking soda', '1t salt'],          'time': None},
            {'desc': 'Add chips',     'ingredients': ['340g choc chips'],                                  'time': None},
            {'desc': 'Bake',          'ingredients': ['scooped dough', 'baking sheet'],                    'time': 660},
        ]
    },
    {
        'name': 'BEEF TACOS',
        'steps': [
            {'desc': 'Brown beef',    'ingredients': ['500g beef', '1t cumin', '1t chili', '1t garlic'],  'time': 480},
            {'desc': 'Warm tortillas','ingredients': ['8 corn tortillas'],                                'time': 120},
            {'desc': 'Toppings',      'ingredients': ['cheese', 'lettuce', 'tomato', 'sour cream', 'lime'], 'time': None},
            {'desc': 'Assemble',      'ingredients': ['beef', 'tortillas', 'toppings', 'hot sauce'],       'time': None},
        ]
    },
]

# ── 3×5 pixel font ────────────────────────────────────────────────────────────
_G = {
    ' ': [0b000,0b000,0b000,0b000,0b000],
    '!': [0b010,0b010,0b010,0b000,0b010],
    "'": [0b010,0b010,0b000,0b000,0b000],
    '(': [0b001,0b010,0b010,0b010,0b001],
    ')': [0b100,0b010,0b010,0b010,0b100],
    '-': [0b000,0b000,0b111,0b000,0b000],
    '.': [0b000,0b000,0b000,0b000,0b010],
    '/': [0b001,0b001,0b010,0b100,0b100],
    '0': [0b111,0b101,0b101,0b101,0b111],
    '1': [0b010,0b110,0b010,0b010,0b111],
    '2': [0b111,0b001,0b111,0b100,0b111],
    '3': [0b111,0b001,0b111,0b001,0b111],
    '4': [0b101,0b101,0b111,0b001,0b001],
    '5': [0b111,0b100,0b111,0b001,0b111],
    '6': [0b111,0b100,0b111,0b101,0b111],
    '7': [0b111,0b001,0b001,0b001,0b001],
    '8': [0b111,0b101,0b111,0b101,0b111],
    '9': [0b111,0b101,0b111,0b001,0b111],
    ':': [0b000,0b010,0b000,0b010,0b000],
    'A': [0b010,0b101,0b111,0b101,0b101],
    'B': [0b110,0b101,0b110,0b101,0b110],
    'C': [0b011,0b100,0b100,0b100,0b011],
    'D': [0b110,0b101,0b101,0b101,0b110],
    'E': [0b111,0b100,0b110,0b100,0b111],
    'F': [0b111,0b100,0b110,0b100,0b100],
    'G': [0b011,0b100,0b101,0b101,0b011],
    'H': [0b101,0b101,0b111,0b101,0b101],
    'I': [0b111,0b010,0b010,0b010,0b111],
    'J': [0b001,0b001,0b001,0b101,0b010],
    'K': [0b101,0b110,0b100,0b110,0b101],
    'L': [0b100,0b100,0b100,0b100,0b111],
    'M': [0b101,0b111,0b101,0b101,0b101],
    'N': [0b110,0b101,0b101,0b101,0b011],
    'O': [0b010,0b101,0b101,0b101,0b010],
    'P': [0b110,0b101,0b110,0b100,0b100],
    'Q': [0b010,0b101,0b101,0b111,0b011],
    'R': [0b110,0b101,0b110,0b101,0b101],
    'S': [0b011,0b100,0b010,0b001,0b110],
    'T': [0b111,0b010,0b010,0b010,0b010],
    'U': [0b101,0b101,0b101,0b101,0b111],
    'V': [0b101,0b101,0b101,0b010,0b010],
    'W': [0b101,0b101,0b101,0b111,0b101],
    'X': [0b101,0b101,0b010,0b101,0b101],
    'Y': [0b101,0b101,0b010,0b010,0b010],
    'Z': [0b111,0b001,0b010,0b100,0b111],
    'a': [0b000,0b011,0b101,0b101,0b011],
    'b': [0b100,0b110,0b101,0b101,0b110],
    'c': [0b000,0b011,0b100,0b100,0b011],
    'd': [0b001,0b011,0b101,0b101,0b011],
    'e': [0b000,0b111,0b101,0b110,0b011],
    'f': [0b011,0b010,0b111,0b010,0b010],
    'g': [0b000,0b011,0b101,0b011,0b001],
    'h': [0b100,0b110,0b101,0b101,0b101],
    'i': [0b010,0b000,0b110,0b010,0b111],
    'j': [0b001,0b000,0b001,0b101,0b010],
    'k': [0b100,0b101,0b110,0b110,0b101],
    'l': [0b110,0b010,0b010,0b010,0b111],
    'm': [0b000,0b111,0b111,0b101,0b101],
    'n': [0b000,0b110,0b101,0b101,0b101],
    'o': [0b000,0b010,0b101,0b101,0b010],
    'p': [0b000,0b110,0b101,0b110,0b100],
    'q': [0b000,0b011,0b101,0b011,0b001],
    'r': [0b000,0b011,0b100,0b100,0b100],
    's': [0b000,0b011,0b110,0b001,0b110],
    't': [0b010,0b111,0b010,0b010,0b001],
    'u': [0b000,0b101,0b101,0b101,0b011],
    'v': [0b000,0b101,0b101,0b010,0b010],
    'w': [0b000,0b101,0b101,0b111,0b101],
    'x': [0b000,0b101,0b010,0b010,0b101],
    'y': [0b000,0b101,0b101,0b011,0b001],
    'z': [0b000,0b111,0b001,0b100,0b111],
}

CHAR_W, CHAR_H, CHAR_GAP = 3, 5, 1


def _text_w(s):
    n = sum(1 for c in s if c in _G)
    return n * (CHAR_W + CHAR_GAP) - CHAR_GAP if n else 0


def _draw_text(img, x, y, text, color, clip_right=64):
    cx = x
    for ch in text:
        rows = _G.get(ch)
        if rows is None:
            cx += CHAR_W + CHAR_GAP
            continue
        for ri, bits in enumerate(rows):
            for ci in range(CHAR_W):
                if bits & (1 << (CHAR_W - 1 - ci)):
                    px, py = cx + ci, y + ri
                    if 0 <= px < clip_right and 0 <= py < 32:
                        img.putpixel((px, py), color)
        cx += CHAR_W + CHAR_GAP
    return cx


def _truncate(text, max_w):
    while text and _text_w(text) > max_w:
        text = text[:-1]
    return text


def load_state():
    try:
        return json.loads(open(STATE_FILE).read())
    except Exception:
        return {'recipe_idx': 0, 'step_idx': 0,
                'timer_running': False, 'timer_end': None, 'timer_total': None}


def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception:
        pass


def _draw_left(img, recipe, step, step_idx, n_steps, t):
    d = ImageDraw.Draw(img)

    # Header bar y=0..5: recipe name on dark gold background
    d.rectangle([(0, 0), (CONTENT_W - 1, 6)], fill=(22, 12, 0))
    name = recipe['name']
    nw   = _text_w(name)
    nx   = max(1, (CONTENT_W - nw) // 2)
    _draw_text(img, nx, 1, name, (255, 185, 0), clip_right=CONTENT_W)

    # Step line y=8..12: "N/M" in cyan + scrolling description in white
    counter  = f"{step_idx + 1}/{n_steps}"
    cx_end   = _draw_text(img, 1, 8, counter, (0, 210, 255), clip_right=CONTENT_W)
    desc     = step['desc']
    desc_x   = cx_end + 2
    desc_max = CONTENT_W - desc_x - 1
    full_dw  = _text_w(desc)

    if full_dw <= desc_max:
        _draw_text(img, desc_x, 8, desc, (255, 255, 255), clip_right=CONTENT_W)
    else:
        cycle  = full_dw - desc_max + 12
        raw    = int((t * 14) % (cycle * 2))
        px_off = raw if raw < cycle else cycle
        _draw_text(img, desc_x - px_off, 8, desc, (255, 255, 255), clip_right=CONTENT_W)

    # Separator y=14
    d.line([(0, 14), (CONTENT_W - 1, 14)], fill=(35, 35, 35))

    # Ingredient rows y=15, 21, 27 — index-scroll when >3 items
    ingredients = step['ingredients']
    if not ingredients:
        msg = 'No extras'
        mw  = _text_w(msg)
        _draw_text(img, (CONTENT_W - mw) // 2, 20, msg, (60, 60, 60), clip_right=CONTENT_W)
        return

    n      = len(ingredients)
    offset = int(t / 2.0) % n if n > 3 else 0
    for i, row_y in enumerate((15, 21, 27)):
        ingr = _truncate(ingredients[(offset + i) % n], CONTENT_W - 3)
        _draw_text(img, 2, row_y, ingr, (55, 230, 90), clip_right=CONTENT_W)


def _draw_timer(img, state, t):
    running     = state.get('timer_running', False)
    timer_end   = state.get('timer_end')
    timer_total = state.get('timer_total')

    if timer_end is not None and timer_total is not None:
        remaining = max(0.0, timer_end - t)
        mins  = int(remaining) // 60
        secs  = int(remaining) % 60
        m_str = f"{mins:02d}"
        s_str = f"{secs:02d}"
        if running and remaining > 0:
            color = (50, 220, 80)
        elif remaining <= 0:
            color = (255, 50, 50) if int(t * 3) % 2 else (160, 0, 0)
        else:
            color = (155, 155, 155)
    else:
        m_str = "--"
        s_str = "--"
        color = (45, 45, 45)

    def draw_char2(ch, dx, dy):
        rows = _G.get(ch)
        if not rows:
            return
        for ri, bits in enumerate(rows):
            for ci in range(CHAR_W):
                if bits & (1 << (CHAR_W - 1 - ci)):
                    for sy in range(2):
                        for sx in range(2):
                            px = TIMER_X + dx + ci * 2 + sx
                            py = dy + ri * 2 + sy
                            if TIMER_X <= px < 64 and 0 <= py < 32:
                                img.putpixel((px, py), color)

    # Two digits at dx=1 and dx=8 (6px wide each, 1px gap at dx=7)
    draw_char2(m_str[0], 1, 1)
    draw_char2(m_str[1], 8, 1)
    # Colon dots centered between digit groups
    img.putpixel((TIMER_X + 7, 12), color)
    img.putpixel((TIMER_X + 7, 14), color)
    draw_char2(s_str[0], 1, 17)
    draw_char2(s_str[1], 8, 17)


def make_frame(state, t):
    img    = Image.new("RGB", (64, 32), (0, 0, 0))
    r_idx  = max(0, min(state.get('recipe_idx', 0), len(RECIPES) - 1))
    s_idx  = state.get('step_idx', 0)
    recipe = RECIPES[r_idx]
    s_idx  = max(0, min(s_idx, len(recipe['steps']) - 1))

    _draw_left(img, recipe, recipe['steps'][s_idx], s_idx, len(recipe['steps']), t)

    ImageDraw.Draw(img).line([(DIVIDER_X, 0), (DIVIDER_X, 31)], fill=(25, 25, 25))

    _draw_timer(img, state, t)
    return img


def main():
    opts = RGBMatrixOptions()
    opts.rows = 32
    opts.cols = 64
    opts.hardware_mapping = 'adafruit-hat'
    try:
        opts.brightness = int(open('/tmp/tidabit_brightness').read().strip())
    except Exception:
        opts.brightness = 80
    opts.pwm_bits = 7

    matrix = RGBMatrix(options=opts)
    canvas = matrix.CreateFrameCanvas()

    state       = load_state()
    last_reload = time.time()

    try:
        while True:
            t = time.time()

            if t - last_reload >= 0.5:
                state       = load_state()
                last_reload = t

            # Auto-advance when a timed step completes
            if state.get('timer_running') and state.get('timer_end'):
                if t >= state['timer_end']:
                    r_idx  = max(0, min(state.get('recipe_idx', 0), len(RECIPES) - 1))
                    recipe = RECIPES[r_idx]
                    next_s = state.get('step_idx', 0) + 1
                    if next_s < len(recipe['steps']):
                        state['step_idx']    = next_s
                        state['timer_total'] = recipe['steps'][next_s].get('time')
                    state['timer_running'] = False
                    state['timer_end']     = None
                    save_state(state)

            canvas.SetImage(make_frame(state, t))
            canvas = matrix.SwapOnVSync(canvas)
            check_and_show_notification(matrix, canvas)
            time.sleep(0.05)

    except KeyboardInterrupt:
        matrix.Clear()


if __name__ == '__main__':
    main()
