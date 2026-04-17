#!/usr/bin/env python3
"""
spotify.py — Spotify now-playing display.
Layout: 32x32 album art (left) | song title, artist, progress bar (right).
"""
import base64
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from PIL import Image, ImageDraw

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    from notify import check_and_show_notification
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
    def check_and_show_notification(m, c): pass

TOKENS_FILE   = "/etc/spotify_tokens.json"
POLL_INTERVAL = 5.0
UI_V2         = True   # False = original layout, True = smaller art / larger text

# V1 layout
ART_SIZE      = 32
TEXT_X        = 34
TEXT_W        = 29

# V2 layout (art 20% smaller, 2px left buffer, vertically centered, wider text panel)
ART_SIZE_V2   = 26
ART_X_V2      = 2
ART_Y_V2      = (32 - ART_SIZE_V2) // 2   # = 3, centers 26px in 32px
TEXT_X_V2     = ART_X_V2 + ART_SIZE_V2 + 2  # = 29
TEXT_W_V2     = 64 - TEXT_X_V2 - 1          # = 34, leaves 1px right margin

# ── 3x5 pixel font (3px wide, 5px tall, 1px gap = 4px/char) ──────────────────
_G = {
    ' ': [0b000,0b000,0b000,0b000,0b000],
    '!': [0b010,0b010,0b010,0b000,0b010],
    '"': [0b101,0b101,0b000,0b000,0b000],
    '#': [0b101,0b111,0b101,0b111,0b101],
    "'": [0b010,0b010,0b000,0b000,0b000],
    '(': [0b001,0b010,0b010,0b010,0b001],
    ')': [0b100,0b010,0b010,0b010,0b100],
    '*': [0b000,0b101,0b010,0b101,0b000],
    '+': [0b000,0b010,0b111,0b010,0b000],
    ',': [0b000,0b000,0b000,0b010,0b100],
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
    ';': [0b000,0b010,0b000,0b010,0b100],
    '=': [0b000,0b111,0b000,0b111,0b000],
    '?': [0b111,0b001,0b011,0b000,0b010],
    '@': [0b111,0b101,0b111,0b100,0b111],
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
    '&': [0b010,0b101,0b010,0b101,0b011],
    '_': [0b000,0b000,0b000,0b000,0b111],
    '|': [0b010,0b010,0b010,0b010,0b010],
    '~': [0b000,0b010,0b101,0b100,0b000],
}

CHAR_W = 3
CHAR_H = 5
CHAR_GAP = 1

# ── 3x3 small font for artist name ───────────────────────────────────────────
_SMALL = {
    ' ': [0b000,0b000,0b000],
    '!': [0b010,0b010,0b000],
    "'": [0b010,0b000,0b000],
    '(': [0b011,0b010,0b011],
    ')': [0b110,0b010,0b110],
    '-': [0b000,0b111,0b000],
    '.': [0b000,0b000,0b010],
    '/': [0b001,0b010,0b100],
    '&': [0b101,0b011,0b101],
    '0': [0b111,0b101,0b111],
    '1': [0b110,0b010,0b111],
    '2': [0b110,0b011,0b111],
    '3': [0b111,0b011,0b111],
    '4': [0b101,0b111,0b001],
    '5': [0b111,0b110,0b011],
    '6': [0b011,0b111,0b101],
    '7': [0b111,0b001,0b010],
    '8': [0b111,0b010,0b111],
    '9': [0b111,0b011,0b001],
    'A': [0b010,0b111,0b101],
    'B': [0b110,0b111,0b110],
    'C': [0b011,0b100,0b011],
    'D': [0b110,0b101,0b110],
    'E': [0b111,0b110,0b111],
    'F': [0b111,0b110,0b100],
    'G': [0b011,0b101,0b011],
    'H': [0b101,0b111,0b101],
    'I': [0b111,0b010,0b111],
    'J': [0b001,0b001,0b110],
    'K': [0b101,0b110,0b101],
    'L': [0b100,0b100,0b111],
    'M': [0b111,0b111,0b101],
    'N': [0b110,0b101,0b011],
    'O': [0b010,0b101,0b010],
    'P': [0b111,0b111,0b100],
    'Q': [0b010,0b101,0b011],
    'R': [0b110,0b111,0b101],
    'S': [0b011,0b010,0b110],
    'T': [0b111,0b010,0b010],
    'U': [0b101,0b101,0b111],
    'V': [0b101,0b101,0b010],
    'W': [0b101,0b101,0b111],
    'X': [0b101,0b010,0b101],
    'Y': [0b101,0b010,0b010],
    'Z': [0b111,0b011,0b111],
    'a': [0b011,0b111,0b011],
    'b': [0b100,0b110,0b111],
    'c': [0b011,0b100,0b011],
    'd': [0b001,0b011,0b111],
    'e': [0b000,0b111,0b110],
    'f': [0b011,0b111,0b010],
    'g': [0b000,0b011,0b001],
    'h': [0b100,0b110,0b101],
    'i': [0b010,0b010,0b010],
    'j': [0b001,0b001,0b011],
    'k': [0b101,0b110,0b101],
    'l': [0b110,0b010,0b011],
    'm': [0b000,0b111,0b101],
    'n': [0b000,0b110,0b101],
    'o': [0b010,0b101,0b010],
    'p': [0b000,0b110,0b100],
    'q': [0b000,0b011,0b001],
    'r': [0b000,0b011,0b100],
    's': [0b000,0b011,0b110],
    't': [0b111,0b010,0b010],
    'u': [0b000,0b101,0b011],
    'v': [0b000,0b101,0b010],
    'w': [0b000,0b101,0b111],
    'x': [0b101,0b010,0b101],
    'y': [0b000,0b101,0b001],
    'z': [0b000,0b111,0b011],
}
SMALL_W = 3
SMALL_H = 3
SMALL_GAP = 1

def _small_str_width(s):
    return sum((SMALL_W + SMALL_GAP) if c in _SMALL else 0 for c in s) - SMALL_GAP

def _truncate_small(text, max_w):
    if _small_str_width(text) <= max_w:
        return text
    while text and _small_str_width(text + '..') > max_w:
        text = text[:-1]
    return text + '..'

def _draw_small_text(img, x, y, text, color):
    iw, ih = img.size
    cx = x
    for ch in text:
        rows = _SMALL.get(ch)
        if rows is None:
            cx += SMALL_W + SMALL_GAP
            continue
        for row_i, bits in enumerate(rows):
            for col_i in range(SMALL_W):
                if bits & (1 << (SMALL_W - 1 - col_i)):
                    px, py = cx + col_i, y + row_i
                    if 0 <= px < iw and 0 <= py < ih:
                        img.putpixel((px, py), color)
        cx += SMALL_W + SMALL_GAP

def _glyph_width(ch):
    return CHAR_W + CHAR_GAP if ch in _G else 0

def _str_width(s):
    return sum(_glyph_width(c) for c in s) - CHAR_GAP  # no trailing gap

def _draw_px_text(img, x, y, text, color):
    iw, ih = img.size
    cx = x
    for ch in text:
        rows = _G.get(ch)
        if rows is None:
            cx += CHAR_W + CHAR_GAP
            continue
        for row_i, bits in enumerate(rows):
            for col_i in range(CHAR_W):
                if bits & (1 << (CHAR_W - 1 - col_i)):
                    px, py = cx + col_i, y + row_i
                    if 0 <= px < iw and 0 <= py < ih:
                        img.putpixel((px, py), color)
        cx += CHAR_W + CHAR_GAP


# ── Token management ──────────────────────────────────────────────────────────

def _load_tokens():
    with open(TOKENS_FILE) as f:
        return json.load(f)

def _refresh_access_token(tokens):
    creds = base64.b64encode(f"{tokens['client_id']}:{tokens['client_secret']}".encode()).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        }).encode(),
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data["access_token"], time.time() + data["expires_in"] - 60


# ── Spotify API ───────────────────────────────────────────────────────────────

def _fetch_currently_playing(access_token):
    req = urllib.request.Request(
        "https://api.spotify.com/v1/me/player/currently-playing",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 204:
                return None
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise
        return None



# ── Album art ─────────────────────────────────────────────────────────────────

_art_cache = {}

def _get_art(url):
    if url in _art_cache:
        return _art_cache[url]
    try:
        with urllib.request.urlopen(url) as resp:
            img = Image.open(io.BytesIO(resp.read())).convert("RGB")
        img = img.resize((ART_SIZE, ART_SIZE), Image.LANCZOS)
        if len(_art_cache) > 5:
            _art_cache.clear()
        _art_cache[url] = img
        return img
    except Exception:
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_ms(ms):
    s = int(ms / 1000)
    return f"{s // 60}:{s % 60:02d}"

def _truncate(text, max_w):
    """Truncate text with '...' to fit max_w pixels."""
    if _str_width(text) <= max_w:
        return text
    while text and _str_width(text + '..') > max_w:
        text = text[:-1]
    return text + '..'

def _build_v2_cache(state):
    """Pre-render title strip and artist image. Called once per track change."""
    title  = state["title"]  or ""
    artist = state["artist"] or ""

    tw = _str_width(title)
    if tw > TEXT_W_V2:
        gap   = TEXT_W_V2 + 8
        total = tw + gap
        strip = Image.new("RGB", (total + TEXT_W_V2, CHAR_H), (0, 0, 0))
        _draw_px_text(strip, 0,        0, title, (255, 255, 255))
        _draw_px_text(strip, tw + gap, 0, title, (255, 255, 255))
        state["_title_strip"]       = strip
        state["_title_strip_total"] = total
    else:
        state["_title_strip"]       = None
        state["_title_strip_total"] = 0

    a_img = Image.new("RGB", (TEXT_W_V2, CHAR_H), (0, 0, 0))
    _draw_px_text(a_img, 0, 0, _truncate(artist, TEXT_W_V2), (140, 140, 140))
    state["_artist_img"] = a_img


# ── Rendering ─────────────────────────────────────────────────────────────────

def make_frame(state, scroll_x):
    img = Image.new("RGB", (64, 32), (0, 0, 0))
    d = ImageDraw.Draw(img)

    # Album art (left 32x32)
    if state["art"]:
        img.paste(state["art"], (0, 0))
    else:
        d.rectangle([0, 0, 31, 31], fill=(25, 25, 25))

    if not state["title"]:
        _draw_px_text(img, TEXT_X, 13, 'no music', (50, 50, 50))
        return img

    # Song title — scroll if wider than panel
    title = state["title"]
    tw = _str_width(title)
    if tw > TEXT_W:
        gap = TEXT_W + 8
        total = tw + gap
        ox = int(scroll_x) % total
        strip = Image.new("RGB", (total + TEXT_W, CHAR_H), (0, 0, 0))
        _draw_px_text(strip, 0, 0, title, (255, 255, 255))
        _draw_px_text(strip, tw + gap, 0, title, (255, 255, 255))
        window = strip.crop((ox, 0, ox + TEXT_W, CHAR_H))
        img.paste(window, (TEXT_X, 1))
    else:
        _draw_px_text(img, TEXT_X, 1, title, (255, 255, 255))

    # Artist — 3x3 small font, truncated
    artist = _truncate_small(state["artist"], TEXT_W)
    _draw_small_text(img, TEXT_X, 8, artist, (140, 140, 140))

    # Progress bar (y:15-16)
    elapsed = state["progress_ms"] + (time.time() - state["fetched_at"]) * 1000
    elapsed = min(elapsed, state["duration_ms"])
    frac = elapsed / state["duration_ms"] if state["duration_ms"] else 0
    bar_w = int(frac * TEXT_W)
    d.rectangle([TEXT_X, 15, TEXT_X + TEXT_W - 1, 16], fill=(50, 50, 50))
    if bar_w > 0:
        d.rectangle([TEXT_X, 15, TEXT_X + bar_w - 1, 16], fill=(30, 215, 96))

    # Elapsed only (~half bar width)
    time_str = _fmt_ms(elapsed)
    tw2 = _str_width(time_str)
    _draw_px_text(img, TEXT_X + TEXT_W - tw2, 19, time_str, (100, 100, 100))

    return img


def make_frame_v2(state, scroll_x):
    img = Image.new("RGB", (64, 32), (0, 0, 0))
    d = ImageDraw.Draw(img)

    # Album art — 26x26, 2px from left edge, vertically centered
    if state["art_small"]:
        img.paste(state["art_small"], (ART_X_V2, ART_Y_V2))
    else:
        d.rectangle([ART_X_V2, ART_Y_V2, ART_X_V2 + ART_SIZE_V2 - 1, ART_Y_V2 + ART_SIZE_V2 - 1], fill=(25, 25, 25))

    if not state["title"]:
        _draw_px_text(img, TEXT_X_V2, 13, 'no music', (50, 50, 50))
        return img

    # Title — crop from pre-rendered strip (no putpixel per frame)
    strip = state.get("_title_strip")
    if strip:
        ox = int(scroll_x) % state["_title_strip_total"]
        img.paste(strip.crop((ox, 0, ox + TEXT_W_V2, CHAR_H)), (TEXT_X_V2, 1))
    else:
        _draw_px_text(img, TEXT_X_V2, 1, state["title"], (255, 255, 255))

    # Artist — paste pre-rendered image
    if state.get("_artist_img"):
        img.paste(state["_artist_img"], (TEXT_X_V2, 9))

    # Progress bar (y:18-19)
    elapsed = state["progress_ms"] + (time.time() - state["fetched_at"]) * 1000
    elapsed = min(elapsed, state["duration_ms"])
    frac = elapsed / state["duration_ms"] if state["duration_ms"] else 0
    bar_w = int(frac * TEXT_W_V2)
    d.rectangle([TEXT_X_V2, 18, TEXT_X_V2 + TEXT_W_V2 - 1, 19], fill=(50, 50, 50))
    if bar_w > 0:
        d.rectangle([TEXT_X_V2, 18, TEXT_X_V2 + bar_w - 1, 19], fill=(30, 215, 96))

    # Elapsed time — right-aligned
    time_str = _fmt_ms(elapsed)
    tw2 = _str_width(time_str)
    _draw_px_text(img, TEXT_X_V2 + TEXT_W_V2 - tw2, 23, time_str, (100, 100, 100))

    return img


# ── Main ──────────────────────────────────────────────────────────────────────

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

    tokens = _load_tokens()
    access_token, token_expires = _refresh_access_token(tokens)

    state = {
        "title": None, "artist": None, "art": None, "art_small": None,
        "progress_ms": 0, "duration_ms": 1,
        "fetched_at": time.time(),
        "_title_strip": None, "_title_strip_total": 0, "_artist_img": None,
    }

    last_poll  = 0.0
    scroll_x   = 0.0
    last_frame = time.time()
    art_url    = None

    try:
        while True:
            now = time.time()
            dt = now - last_frame
            last_frame = now

            if now >= token_expires:
                access_token, token_expires = _refresh_access_token(tokens)

            if now - last_poll >= POLL_INTERVAL:
                last_poll = now
                try:
                    data = _fetch_currently_playing(access_token)
                    if data and data.get("item"):
                        item = data["item"]
                        state["title"]       = item["name"]
                        state["artist"]      = item["artists"][0]["name"]
                        state["progress_ms"] = data["progress_ms"]
                        state["duration_ms"] = item["duration_ms"]
                        state["fetched_at"]  = now
                        new_url = item["album"]["images"][-1]["url"]
                        if new_url != art_url:
                            art_url            = new_url
                            state["art"]       = _get_art(art_url)
                            if state["art"]:
                                small = state["art"].resize((ART_SIZE_V2, ART_SIZE_V2), Image.LANCZOS)
                                state["art_small"] = small
                            else:
                                state["art_small"] = None
                        _build_v2_cache(state)
                    else:
                        state["title"] = None
                        _build_v2_cache(state)
                except urllib.error.HTTPError as e:
                    if e.code == 401:
                        access_token, token_expires = _refresh_access_token(tokens)

            # Advance title scroll at 18px/sec
            if state["title"] and _str_width(state["title"]) > TEXT_W:
                scroll_x += dt * 18
            else:
                scroll_x = 0.0

            canvas.SetImage(make_frame_v2(state, scroll_x) if UI_V2 else make_frame(state, scroll_x))
            canvas = matrix.SwapOnVSync(canvas)
            check_and_show_notification(matrix, canvas)
            time.sleep(0.05)

    except KeyboardInterrupt:
        matrix.Clear()


if __name__ == "__main__":
    main()
