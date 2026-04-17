#!/usr/bin/env python3
"""
timer.py — Countdown timer with starfield background.
Done state: looping herd of cows across a pasture.
10s after timer ends, a UFO sweeps in and incinerates a cow.
Reads /tmp/tidabit_timer JSON: {"end": timestamp, "total": seconds}
"""
import json
import math
import random
import time
from PIL import Image, ImageDraw

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    from notify import check_and_show_notification
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
    def check_and_show_notification(m, c): pass

TIMER_FILE = '/tmp/tidabit_timer'

# ── 3×5 font (digits + colon only) ───────────────────────────────────────────
_G = {
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
}
CHAR_W, CHAR_H, CHAR_GAP = 3, 5, 1

def _str_width(s):
    return sum(CHAR_W + CHAR_GAP for c in s if c in _G) - CHAR_GAP

def _draw_px_text(img, x, y, text, color):
    iw, ih = img.size
    cx = x
    for ch in text:
        rows = _G.get(ch)
        if not rows:
            cx += CHAR_W + CHAR_GAP
            continue
        for ri, bits in enumerate(rows):
            for ci in range(CHAR_W):
                if bits & (1 << (CHAR_W - 1 - ci)):
                    px, py = cx + ci, y + ri
                    if 0 <= px < iw and 0 <= py < ih:
                        img.putpixel((px, py), color)
        cx += CHAR_W + CHAR_GAP

def _draw_big(img, text, color, scale=3):
    w = _str_width(text)
    if w <= 0:
        return
    tmp = Image.new("RGB", (w, CHAR_H), (0, 0, 0))
    _draw_px_text(tmp, 0, 0, text, color)
    big = tmp.resize((w * scale, CHAR_H * scale), Image.NEAREST)
    x = (64 - w * scale) // 2
    y = (32 - CHAR_H * scale) // 2
    img.paste(big, (x, y))


# ── Stars ─────────────────────────────────────────────────────────────────────
def _make_stars(n=35, seed=17):
    rng = random.Random(seed)
    return [
        (rng.randint(0, 63), rng.randint(0, 27),
         rng.uniform(0, math.pi * 2), rng.uniform(1.2, 3.5))
        for _ in range(n)
    ]

_STARS = _make_stars()


# ── Cow sprites (12×8, facing right) ─────────────────────────────────────────
_W = (230, 225, 200)
_B = (25,  25,  25)
_P = (230, 150, 140)
_COW_CMAP = {'B': _B, 'W': _W, 'P': _P}
COW_W, COW_H = 12, 8
COW_Y   = 15   # y where cows are drawn
GRASS_Y = 23   # top of grass

_COW_ROWS_A = [          # legs together
    '............',
    '.......BBBB.',
    '......BPPBB.',
    'BWWWWWWBBBB.',
    'BWWWBWWWWWB.',
    'BWWWWWWWWWB.',
    '.BB.....BB..',
    '.BB.....BB..',
]
_COW_ROWS_B = [          # legs striding
    '............',
    '.......BBBB.',
    '......BPPBB.',
    'BWWWWWWBBBB.',
    'BWWWBWWWWWB.',
    'BWWWWWWWWWB.',
    '..BB...B.B..',
    '..BB....B...',
]

def _make_cow(rows):
    img = Image.new('RGBA', (COW_W, COW_H), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            c = _COW_CMAP.get(ch)
            if c:
                img.putpixel((x, y), c + (255,))
    return img

_COW_IMGS = [_make_cow(_COW_ROWS_A), _make_cow(_COW_ROWS_B)]


# ── UFO sprite (14×5) ─────────────────────────────────────────────────────────
UFO_W, UFO_H = 14, 5

_DM = (140, 200, 255)   # dome — pale blue
_SV = (185, 185, 190)   # silver hull
_LG = (255, 240,  80)   # yellow lights
_EM = (200, 255, 160)   # beam emitter tip

_UFO_ROWS = [
    '.....DDDD.....',   # dome
    '..SSSSSSSSSS..',   # upper hull
    'SSSSLLLLLLSSSS',   # widest — lights in belly
    '..SSSSSSSSSS..',   # lower hull
    '.....EEEE.....',   # beam emitter
]
_UFO_CMAP = {'D': _DM, 'S': _SV, 'L': _LG, 'E': _EM}

def _make_ufo_img():
    img = Image.new('RGBA', (UFO_W, UFO_H), (0, 0, 0, 0))
    for y, row in enumerate(_UFO_ROWS):
        for x, ch in enumerate(row):
            c = _UFO_CMAP.get(ch)
            if c:
                img.putpixel((x, y), c + (255,))
    return img

_UFO_IMG = _make_ufo_img()

# Belly light pixel coords relative to UFO origin (row 2, x=4..9)
_UFO_LIGHT_PXS = [(x, 2) for x in range(4, 10)]


# ── Herd state ────────────────────────────────────────────────────────────────
_rng = random.Random(55)

def _init_herd():
    return [
        {'x': float(-COW_W - i * 18 - _rng.randint(0, 12)),
         'speed': 7.0 + _rng.random() * 3.0,
         'zapped': False,
         'frozen_x': 0.0}
        for i in range(6)
    ]

_herd = _init_herd()


def _advance_herd(dt):
    for cow in _herd:
        if cow['zapped']:
            continue
        cow['x'] += cow['speed'] * dt
        if cow['x'] > 64 + COW_W:
            cow['x'] = float(-COW_W - _rng.randint(5, 30))


# ── UFO state ─────────────────────────────────────────────────────────────────
# phases: idle → approach → hover → beam → retreat → done
_ufo = {
    'phase':    'idle',
    'x':         78.0,
    'y':          2.0,
    'target_x':  25.0,
    'zap_idx':   None,
    'beam_len':   0.0,
    'phase_t':    0.0,
    'done':      False,
}


def _start_ufo():
    candidates = [i for i, c in enumerate(_herd)
                  if 8 <= c['x'] <= 48 and not c['zapped']]
    if not candidates:
        candidates = [i for i, c in enumerate(_herd) if not c['zapped']]
    zap_idx = candidates[0] if candidates else None

    if zap_idx is not None:
        cx = _herd[zap_idx]['x'] + COW_W // 2 - UFO_W // 2
        target_x = max(2.0, min(64.0 - UFO_W - 2, cx))
    else:
        target_x = 25.0

    _ufo.update({
        'phase':   'approach',
        'x':        78.0,
        'y':         2.0,
        'target_x': target_x,
        'zap_idx':  zap_idx,
        'beam_len':  0.0,
        'phase_t':   0.0,
        'done':     False,
    })


def _advance_ufo(dt):
    u = _ufo
    u['phase_t'] += dt
    pt = u['phase_t']

    if u['phase'] == 'approach':
        dx = u['target_x'] - u['x']
        step = 40.0 * dt
        if abs(dx) <= step:
            u['x'] = u['target_x']
            u['phase'] = 'hover'
            u['phase_t'] = 0.0
        else:
            u['x'] += math.copysign(step, dx)

    elif u['phase'] == 'hover':
        if pt >= 0.4:
            u['phase'] = 'beam'
            u['phase_t'] = 0.0

    elif u['phase'] == 'beam':
        max_beam = float(GRASS_Y - (int(u['y']) + UFO_H))
        if pt < 0.6:
            u['beam_len'] = (pt / 0.6) * max_beam
        elif pt < 1.0:
            u['beam_len'] = max_beam
            zi = u['zap_idx']
            if zi is not None and not _herd[zi]['zapped']:
                _herd[zi]['zapped']   = True
                _herd[zi]['frozen_x'] = _herd[zi]['x']
        elif pt < 1.4:
            u['beam_len'] = max(0.0, (1.4 - pt) / 0.4 * max_beam)
        else:
            u['beam_len'] = 0.0
            u['phase'] = 'retreat'
            u['phase_t'] = 0.0

    elif u['phase'] == 'retreat':
        speed = 35.0 + pt * 110.0    # accelerates rapidly off right
        u['x'] += speed * dt
        if u['x'] > 70.0:
            u['phase'] = 'done'
            u['done']  = True
            zi = u['zap_idx']
            if zi is not None:
                _herd[zi]['zapped'] = False
                _herd[zi]['x']      = float(-COW_W - _rng.randint(10, 40))


# ── Rendering ─────────────────────────────────────────────────────────────────
def make_countdown_frame(remaining, total):
    img = Image.new("RGB", (64, 32), (0, 0, 0))
    t = time.time()

    for sx, sy, phase, speed in _STARS:
        b = int(((math.sin(t * speed + phase) + 1) / 2) * 180 + 40)
        img.putpixel((sx, sy), (b, b, b))

    r    = max(0, math.ceil(remaining))
    mins = r // 60
    secs = r % 60
    _draw_big(img, f"{mins:02d}:{secs:02d}", (255, 255, 255), scale=3)

    frac = max(0.0, remaining / total) if total > 0 else 0.0
    bar_w = int(frac * 62)
    d = ImageDraw.Draw(img)
    d.rectangle([1, 30, 62, 31], fill=(40, 40, 40))
    if bar_w > 0:
        d.rectangle([1, 30, bar_w, 31], fill=(255, 255, 255))

    return img


def make_cow_frame():
    img = Image.new("RGB", (64, 32), (3, 5, 18))
    t   = time.time()
    d   = ImageDraw.Draw(img)
    u   = _ufo

    # Stars (sky only)
    for sx, sy, phase, speed in _STARS:
        if sy < 22:
            b = int(((math.sin(t * speed + phase) + 1) / 2) * 140 + 25)
            img.putpixel((sx, sy), (b, b, b))

    # Grass
    d.rectangle([0, 23, 63, 24], fill=(55, 150, 30))
    d.rectangle([0, 25, 63, 31], fill=(28, 88, 15))

    # ── Beam (drawn under cows so beam disappears behind them) ────────────────
    if u['phase'] == 'beam' and u['beam_len'] > 0:
        ufo_cx     = int(u['x']) + UFO_W // 2
        beam_top   = int(u['y']) + UFO_H
        beam_bot   = beam_top + int(u['beam_len'])
        bl         = u['beam_len']
        half_outer = max(1, int(bl * 4.0 / 16.0))
        half_inner = max(1, int(bl * 2.0 / 16.0))
        # Outer glow
        d.polygon([(ufo_cx, beam_top),
                   (ufo_cx - half_outer, beam_bot),
                   (ufo_cx + half_outer, beam_bot)],
                  fill=(50, 110, 30))
        # Inner bright beam
        d.polygon([(ufo_cx, beam_top),
                   (ufo_cx - half_inner, beam_bot),
                   (ufo_cx + half_inner, beam_bot)],
                  fill=(180, 255, 100))

    # ── Cows ──────────────────────────────────────────────────────────────────
    walk    = int(t * 4) % 2
    cow_img = _COW_IMGS[walk]

    for cow in sorted(_herd, key=lambda c: c['x']):
        if cow['zapped']:
            continue
        cx    = int(cow['x'])
        src_x = max(0, -cx)
        dst_x = max(0, cx)
        w     = min(COW_W - src_x, 64 - dst_x)
        if w > 0:
            region = cow_img.crop((src_x, 0, src_x + w, COW_H))
            img.paste(region, (dst_x, COW_Y), region)

    # ── Incineration flash (over cow, under UFO sprite) ───────────────────────
    if u['phase'] == 'beam':
        pt = u['phase_t']
        zi = u['zap_idx']
        if zi is not None and 0.6 <= pt < 1.0:
            fx = int(_herd[zi]['frozen_x'])
            frac = (pt - 0.6) / 0.4   # 0 → 1 across the hold window
            if frac < 0.35:
                # White-hot flash
                col = (255, 255, 255)
            elif frac < 0.65:
                # Orange
                col = (255, 140, 0)
            else:
                # Fading ember
                v   = int(180 * (1.0 - (frac - 0.65) / 0.35))
                col = (v, v // 3, 0)
            for fy in range(COW_Y, COW_Y + COW_H):
                for fx2 in range(fx, fx + COW_W):
                    if 0 <= fx2 < 64 and 0 <= fy < 32:
                        img.putpixel((fx2, fy), col)

    # ── UFO sprite ────────────────────────────────────────────────────────────
    if u['phase'] not in ('idle', 'done'):
        ux    = int(u['x'])
        uy    = int(u['y'])
        # Hover bob
        if u['phase'] == 'hover':
            uy += int(math.sin(u['phase_t'] * 12) * 1)

        src_x = max(0, -ux)
        dst_x = max(0, ux)
        w     = min(UFO_W - src_x, 64 - dst_x)
        if w > 0:
            region = _UFO_IMG.crop((src_x, 0, src_x + w, UFO_H))
            img.paste(region, (dst_x, uy), region)

        # Animate belly lights — flicker during beam phase
        light_col = _LG
        if u['phase'] == 'beam':
            light_col = (255, 255, 255) if int(time.time() * 10) % 2 == 0 else (255, 200, 50)
        for lx, ly in _UFO_LIGHT_PXS:
            px, py = ux + lx, uy + ly
            if 0 <= px < 64 and 0 <= py < 32:
                img.putpixel((px, py), light_col)

    return img


# ── Timer file ────────────────────────────────────────────────────────────────
def _load_timer():
    try:
        data = json.loads(open(TIMER_FILE).read())
        return float(data['end']), float(data['total'])
    except Exception:
        return None, None


# ── Main ──────────────────────────────────────────────────────────────────────
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

    last_t     = time.time()
    done_since = None   # when remaining first hit 0
    next_ufo_t = None   # scheduled timestamp for next UFO visit

    try:
        while True:
            now    = time.time()
            dt     = now - last_t
            last_t = now

            end_time, total = _load_timer()
            remaining = (end_time - now) if end_time else -1

            if remaining > 0:
                # Active countdown — reset UFO/done state for next run
                done_since = None
                next_ufo_t = None
                if _ufo['phase'] != 'idle' or _ufo['done']:
                    _ufo['phase'] = 'idle'
                    _ufo['done']  = False
                    for cow in _herd:
                        cow['zapped'] = False
                canvas.SetImage(make_countdown_frame(remaining, total))
            else:
                if done_since is None:
                    done_since = now
                    next_ufo_t = done_since + 10.0   # first visit 10s after end

                _advance_herd(dt)

                # If UFO just finished, schedule next random visit
                if _ufo['done']:
                    _ufo['phase'] = 'idle'
                    _ufo['done']  = False
                    next_ufo_t = now + random.uniform(40.0, 180.0)

                # Launch UFO when scheduled
                if next_ufo_t is not None and now >= next_ufo_t and _ufo['phase'] == 'idle':
                    _start_ufo()

                if _ufo['phase'] not in ('idle', 'done'):
                    _advance_ufo(dt)

                canvas.SetImage(make_cow_frame())

            canvas = matrix.SwapOnVSync(canvas)
            check_and_show_notification(matrix, canvas)
            time.sleep(0.05)

    except KeyboardInterrupt:
        matrix.Clear()


if __name__ == "__main__":
    main()
