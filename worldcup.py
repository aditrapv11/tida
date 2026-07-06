#!/usr/bin/env python3
"""worldcup.py — 2026 FIFA World Cup next match display."""

import json
import math
import time
import threading
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from io import BytesIO

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
from notify import check_and_show_notification

# ── Display constants ─────────────────────────────────────────────────────────

ET = ZoneInfo('America/New_York')
FLAG_DIR = Path('/tmp/tidabit_flags')
FLAG_DIR.mkdir(exist_ok=True)

PANEL_W, PANEL_H = 64, 32
FLAG_W, FLAG_H = 18, 12
FONT = ImageFont.load_default(size=8)

# Colors
GREEN  = (0, 180, 70)
GOLD   = (200, 160, 0)
WHITE  = (255, 255, 255)
GRAY   = (80, 80, 80)
DIM    = (40, 40, 40)
BLACK  = (0, 0, 0)

# ── Stadium timezone / city mapping ───────────────────────────────────────────

STADIUM_TZ = {
    '1':  ZoneInfo('America/Chicago'),      # Mexico City
    '2':  ZoneInfo('America/Chicago'),      # Guadalajara
    '3':  ZoneInfo('America/Chicago'),      # Monterrey
    '4':  ZoneInfo('America/Chicago'),      # Dallas
    '5':  ZoneInfo('America/Chicago'),      # Houston
    '6':  ZoneInfo('America/Chicago'),      # Kansas City
    '7':  ZoneInfo('America/New_York'),     # Atlanta
    '8':  ZoneInfo('America/New_York'),     # Miami
    '9':  ZoneInfo('America/New_York'),     # Boston
    '10': ZoneInfo('America/New_York'),     # Philadelphia
    '11': ZoneInfo('America/New_York'),     # New York
    '12': ZoneInfo('America/Toronto'),      # Toronto
    '13': ZoneInfo('America/Vancouver'),    # Vancouver
    '14': ZoneInfo('America/Los_Angeles'),  # Seattle
    '15': ZoneInfo('America/Los_Angeles'),  # San Francisco
    '16': ZoneInfo('America/Los_Angeles'),  # Los Angeles
}

STADIUM_CITY = {
    '1': 'Mexico City', '2': 'Guadalajara', '3': 'Monterrey',
    '4': 'Dallas',      '5': 'Houston',     '6': 'Kansas City',
    '7': 'Atlanta',     '8': 'Miami',       '9': 'Boston',
    '10': 'Philadelphia', '11': 'New York', '12': 'Toronto',
    '13': 'Vancouver',  '14': 'Seattle',    '15': 'San Francisco',
    '16': 'Los Angeles',
}

CITY_SHORT = {
    'Mexico City':   'CDMX',
    'Guadalajara':   'GDL',
    'Monterrey':     'MTY',
    'Kansas City':   'KC',
    'Philadelphia':  'Philly',
    'New York':      'NYC',
    'San Francisco': 'SF',
    'Los Angeles':   'LA',
    'Vancouver':     'Van',
}

# ── Country lookup tables ─────────────────────────────────────────────────────

COUNTRY_TO_FIFA = {
    'Germany': 'GER',    'Brazil': 'BRA',     'Argentina': 'ARG',
    'France': 'FRA',     'Spain': 'ESP',      'England': 'ENG',
    'Italy': 'ITA',      'Netherlands': 'NED','Portugal': 'POR',
    'Belgium': 'BEL',    'Uruguay': 'URU',    'Mexico': 'MEX',
    'United States': 'USA', 'USA': 'USA',     'Canada': 'CAN',
    'Morocco': 'MAR',    'Senegal': 'SEN',    'Ghana': 'GHA',
    'Nigeria': 'NGA',    'Egypt': 'EGY',      'Japan': 'JPN',
    'South Korea': 'KOR','Korea Republic': 'KOR', 'Australia': 'AUS',
    'Saudi Arabia': 'KSA','Iran': 'IRN',       'Qatar': 'QAT',
    'Poland': 'POL',     'Croatia': 'CRO',    'Serbia': 'SRB',
    'Switzerland': 'SUI','Denmark': 'DEN',    'Sweden': 'SWE',
    'Norway': 'NOR',     'Scotland': 'SCO',   'Wales': 'WAL',
    'Austria': 'AUT',    'Turkey': 'TUR',     'Greece': 'GRE',
    'Paraguay': 'PAR',   'Colombia': 'COL',   'Ecuador': 'ECU',
    'Peru': 'PER',       'Chile': 'CHI',      'Bolivia': 'BOL',
    'Venezuela': 'VEN',  'Costa Rica': 'CRC', 'Honduras': 'HON',
    'Guatemala': 'GUA',  'Panama': 'PAN',     'El Salvador': 'SLV',
    'Jamaica': 'JAM',    'Trinidad and Tobago': 'TRI', 'Haiti': 'HAI',
    'Cameroon': 'CMR',   "Ivory Coast": 'CIV',"Cote d'Ivoire": 'CIV',
    'Mali': 'MLI',       'South Africa': 'RSA','Tunisia': 'TUN',
    'Algeria': 'ALG',    'Zambia': 'ZAM',     'New Zealand': 'NZL',
    'Indonesia': 'IDN',  'Thailand': 'THA',   'Ukraine': 'UKR',
    'Romania': 'ROU',    'Hungary': 'HUN',    'Czech Republic': 'CZE',
    'Czechia': 'CZE',    'Slovakia': 'SVK',   'Slovenia': 'SVN',
    'Bosnia and Herzegovina': 'BIH', 'Montenegro': 'MNE',
    'Albania': 'ALB',    'North Macedonia': 'MKD', 'Armenia': 'ARM',
    'Georgia': 'GEO',    'Iceland': 'ISL',    'Finland': 'FIN',
    'Democratic Republic of the Congo': 'COD', 'DR Congo': 'COD',
    'Congo': 'CGO',      'Angola': 'ANG',     'Kenya': 'KEN',
    'Iraq': 'IRQ',       'Jordan': 'JOR',     'United Arab Emirates': 'UAE',
    'China': 'CHN',      'India': 'IND',      'Uzbekistan': 'UZB',
    'Philippines': 'PHI','Vietnam': 'VIE',    'Malaysia': 'MAS',
    'Cuba': 'CUB',       'Suriname': 'SUR',   'Cape Verde': 'CPV',
    'Curacao': 'CUW',    'New Zealand': 'NZL',
}

COUNTRY_TO_ISO2 = {
    'Germany': 'de',     'Brazil': 'br',      'Argentina': 'ar',
    'France': 'fr',      'Spain': 'es',       'England': 'gb-eng',
    'Italy': 'it',       'Netherlands': 'nl', 'Portugal': 'pt',
    'Belgium': 'be',     'Uruguay': 'uy',     'Mexico': 'mx',
    'United States': 'us','USA': 'us',        'Canada': 'ca',
    'Morocco': 'ma',     'Senegal': 'sn',     'Ghana': 'gh',
    'Nigeria': 'ng',     'Egypt': 'eg',       'Japan': 'jp',
    'South Korea': 'kr', 'Korea Republic': 'kr', 'Australia': 'au',
    'Saudi Arabia': 'sa','Iran': 'ir',        'Qatar': 'qa',
    'Poland': 'pl',      'Croatia': 'hr',     'Serbia': 'rs',
    'Switzerland': 'ch', 'Denmark': 'dk',     'Sweden': 'se',
    'Norway': 'no',      'Scotland': 'gb-sct','Wales': 'gb-wls',
    'Austria': 'at',     'Turkey': 'tr',      'Greece': 'gr',
    'Paraguay': 'py',    'Colombia': 'co',    'Ecuador': 'ec',
    'Peru': 'pe',        'Chile': 'cl',       'Bolivia': 'bo',
    'Venezuela': 've',   'Costa Rica': 'cr',  'Honduras': 'hn',
    'Guatemala': 'gt',   'Panama': 'pa',      'El Salvador': 'sv',
    'Jamaica': 'jm',     'Trinidad and Tobago': 'tt', 'Haiti': 'ht',
    'Cameroon': 'cm',    'Ivory Coast': 'ci', "Cote d'Ivoire": 'ci',
    'Mali': 'ml',        'South Africa': 'za','Tunisia': 'tn',
    'Algeria': 'dz',     'Zambia': 'zm',      'New Zealand': 'nz',
    'Indonesia': 'id',   'Thailand': 'th',    'Ukraine': 'ua',
    'Romania': 'ro',     'Hungary': 'hu',     'Czech Republic': 'cz',
    'Czechia': 'cz',     'Slovakia': 'sk',    'Slovenia': 'si',
    'Bosnia and Herzegovina': 'ba', 'Montenegro': 'me',
    'Albania': 'al',     'North Macedonia': 'mk', 'Armenia': 'am',
    'Georgia': 'ge',     'Iceland': 'is',     'Finland': 'fi',
    'Democratic Republic of the Congo': 'cd', 'DR Congo': 'cd',
    'Congo': 'cg',       'Angola': 'ao',      'Kenya': 'ke',
    'Iraq': 'iq',        'Jordan': 'jo',      'United Arab Emirates': 'ae',
    'China': 'cn',       'India': 'in',       'Uzbekistan': 'uz',
    'Philippines': 'ph', 'Vietnam': 'vn',     'Malaysia': 'my',
    'Cuba': 'cu',        'Suriname': 'sr',    'Cape Verde': 'cv',
    'Curacao': 'cw',
}

# ── Matrix setup ──────────────────────────────────────────────────────────────

options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
try:
    options.brightness = int(open('/tmp/tidabit_brightness').read().strip())
except Exception:
    options.brightness = 80
options.pwm_bits = 7
options.hardware_mapping = 'adafruit-hat'
matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# ── State ─────────────────────────────────────────────────────────────────────

state = {'next_game': None, 'last_game': None}
lock = threading.Lock()

# ── API ───────────────────────────────────────────────────────────────────────

def parse_game_dt(game):
    sid = str(game.get('stadium_id', '9'))
    tz  = STADIUM_TZ.get(sid, ZoneInfo('America/New_York'))
    try:
        dt = datetime.strptime(game['local_date'], '%m/%d/%Y %H:%M')
        return dt.replace(tzinfo=tz)
    except Exception:
        return None


def refresh():
    try:
        req = urllib.request.Request(
            'https://worldcup26.ir/get/games',
            headers={'User-Agent': 'tidabit/1.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        games = data.get('games', data) if isinstance(data, dict) else data
    except Exception:
        return

    now = datetime.now(tz=timezone.utc)
    upcoming, past = [], []
    for g in games:
        if not g.get('home_team_name_en') or not g.get('away_team_name_en'):
            continue
        dt = parse_game_dt(g)
        if dt is None:
            continue
        if g.get('finished') == 'TRUE' or dt <= now:
            past.append((dt, g))
        else:
            upcoming.append((dt, g))

    upcoming.sort(key=lambda x: x[0])
    past.sort(key=lambda x: x[0], reverse=True)

    with lock:
        state['next_game'] = upcoming[0][1] if upcoming else None
        state['last_game'] = past[0][1] if past else None


def poll_loop():
    while True:
        refresh()
        time.sleep(300)


threading.Thread(target=poll_loop, daemon=True).start()
time.sleep(3)

# ── Flags ─────────────────────────────────────────────────────────────────────

FLAG_CACHE: dict = {}


def get_flag(country_name: str) -> Image.Image:
    iso2 = COUNTRY_TO_ISO2.get(country_name)
    if not iso2:
        return Image.new('RGB', (FLAG_W, FLAG_H), (60, 60, 60))

    if iso2 in FLAG_CACHE:
        return FLAG_CACHE[iso2]

    cache_path = FLAG_DIR / f'{iso2}.png'
    try:
        img = Image.open(cache_path).convert('RGB')
        if img.size != (FLAG_W, FLAG_H):
            img = img.resize((FLAG_W, FLAG_H), Image.LANCZOS)
            try:
                img.save(cache_path)
            except Exception:
                pass
        FLAG_CACHE[iso2] = img
        return img
    except Exception:
        pass

    try:
        req = urllib.request.Request(
            f'https://flagcdn.com/w40/{iso2}.png',
            headers={'User-Agent': 'tidabit/1.0'})
        with urllib.request.urlopen(req, timeout=6) as r:
            raw = r.read()
        img = Image.open(BytesIO(raw)).convert('RGB').resize(
            (FLAG_W, FLAG_H), Image.LANCZOS)
        try:
            img.save(cache_path)
        except Exception:
            pass
        FLAG_CACHE[iso2] = img
        return img
    except Exception:
        placeholder = Image.new('RGB', (FLAG_W, FLAG_H), (60, 60, 60))
        return placeholder


def preload_flags():
    with lock:
        ng = state.get('next_game')
        lg = state.get('last_game')
    for g in [ng, lg]:
        if g:
            get_flag(g.get('home_team_name_en', ''))
            get_flag(g.get('away_team_name_en', ''))


threading.Thread(target=preload_flags, daemon=True).start()

# ── Drawing helpers ───────────────────────────────────────────────────────────

def ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        suf = 'th'
    else:
        suf = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suf}'


def fifa_code(name: str) -> str:
    return COUNTRY_TO_FIFA.get(name, name[:3].upper())


def draw_game_frame(game: dict) -> Image.Image:
    img  = Image.new('RGB', (PANEL_W, PANEL_H), BLACK)
    draw = ImageDraw.Draw(img)

    home  = game.get('home_team_name_en', '???')
    away  = game.get('away_team_name_en', '???')
    code1 = fifa_code(home)
    code2 = fifa_code(away)
    sid   = str(game.get('stadium_id', '9'))
    city  = STADIUM_CITY.get(sid, '?')
    dt    = parse_game_dt(game)
    dt_et = dt.astimezone(ET) if dt else None

    # ── Top bar (green wave, radiating from center outward) ────────────────────────────────────────────
    t_bar = time.time()
    cx_bar = (PANEL_W - 1) / 2.0
    for bx in range(PANEL_W):
        d = abs(bx - cx_bar)
        wave = 0.5 + 0.5 * math.sin(d * 0.30 - t_bar * 2.6)
        b = 0.18 + 0.82 * wave
        col = (int(GREEN[0] * b), int(GREEN[1] * b), int(GREEN[2] * b))
        draw.line([(bx, 0), (bx, 1)], fill=col)

    # ── Codes row (centered, no flags on this line) ───────────────────────────
    bb1  = draw.textbbox((0, 0), code1, font=FONT)
    bb_v = draw.textbbox((0, 0), 'vs',  font=FONT)
    bb2  = draw.textbbox((0, 0), code2, font=FONT)
    w1, wv, w2 = bb1[2]-bb1[0], bb_v[2]-bb_v[0], bb2[2]-bb2[0]

    total = w1 + 4 + wv + 4 + w2
    x0    = max(0, (PANEL_W - total) // 2)

    x_code1 = x0
    x_vs    = x_code1 + w1 + 4
    x_code2 = x_vs + wv + 4

    ty = 2
    draw.text((x_code1, ty),     code1, fill=WHITE, font=FONT)
    draw.text((x_code2, ty),     code2, fill=WHITE, font=FONT)

    # ── Flags below codes, centered under each code ───────────────────────────
    fy  = 13
    cx1 = x_code1 + w1 // 2
    cx2 = x_code2 + w2 // 2
    fx1 = max(0, cx1 - FLAG_W // 2)
    fx2 = min(PANEL_W - FLAG_W, cx2 - FLAG_W // 2)

    img.paste(get_flag(home), (fx1, fy))
    img.paste(get_flag(away), (fx2, fy))

    # 'vs' centered between the two flags, aligned with them
    vh   = bb_v[3] - bb_v[1]
    vs_x = (fx1 + FLAG_W + fx2) // 2 - wv // 2
    vs_y = fy + (FLAG_H - vh) // 2 - bb_v[1]
    draw.text((vs_x, vs_y), 'vs', fill=WHITE, font=FONT)


    # ── Bottom marquee: time (gold) / date (yellow) / city (gray)
    time_str  = dt_et.strftime('%-I:%M%p').lower() if dt_et else '—'
    date_str  = (dt_et.strftime('%b ') + ordinal(dt_et.day)) if dt_et else ''
    city_disp = CITY_SHORT.get(city, city) + ' Stadium'
    DATE_Y = (240, 210, 0)

    segs = [(time_str, GOLD), (date_str, DATE_Y), (city_disp, (130, 130, 130))]
    segs = [(t, c) for t, c in segs if t]
    GAP  = 7
    ws   = [draw.textbbox((0, 0), t, font=FONT)[2] for t, _ in segs]
    strip_w = sum(ws) + GAP * len(segs)
    strip = Image.new('RGB', (strip_w, 8), BLACK)
    sdraw = ImageDraw.Draw(strip)
    sx = 0
    for (t, c), w in zip(segs, ws):
        sdraw.text((sx, 0), t, fill=c, font=FONT)
        sx += w + GAP

    if strip_w <= PANEL_W:
        img.paste(strip, (1, 24))
    else:
        off = int((time.time() * 8) % strip_w)
        win = Image.new('RGB', (PANEL_W, 8), BLACK)
        win.paste(strip, (-off, 0))
        win.paste(strip, (strip_w - off, 0))
        img.paste(win, (0, 24))

    return img


def draw_no_game_frame() -> Image.Image:
    img  = Image.new('RGB', (PANEL_W, PANEL_H), BLACK)
    draw = ImageDraw.Draw(img)

    with lock:
        ng = state.get('next_game')
        lg = state.get('last_game')

    # Vertical divider
    draw.rectangle([(31, 0), (31, 31)], fill=DIM)

    # ── Left: countdown to next game ──────────────────────────────────────────
    if ng:
        dt  = parse_game_dt(ng)
        now = datetime.now(tz=timezone.utc)
        if dt and dt > now:
            secs  = int((dt - now).total_seconds())
            days  = secs // 86400
            hours = (secs % 86400) // 3600
            mins  = (secs % 3600) // 60
            draw.text((1, 2),  'Next',         fill=GRAY,  font=FONT)
            if days > 0:
                draw.text((1, 10), f'{days}d',     fill=WHITE, font=FONT)
                draw.text((1, 20), f'{hours}h',    fill=GRAY,  font=FONT)
            else:
                draw.text((1, 10), f'{hours}h',    fill=WHITE, font=FONT)
                draw.text((1, 20), f'{mins}m',     fill=GRAY,  font=FONT)
        else:
            draw.text((1, 12), 'Soon', fill=GREEN, font=FONT)
    else:
        draw.text((1, 2),  'WC',   fill=GRAY, font=FONT)
        draw.text((1, 12), 'over', fill=GRAY, font=FONT)

    # ── Right: last result ────────────────────────────────────────────────────
    if lg:
        c1 = fifa_code(lg.get('home_team_name_en', '???'))
        c2 = fifa_code(lg.get('away_team_name_en', '???'))
        s1 = lg.get('home_score', '?')
        s2 = lg.get('away_score', '?')
        draw.text((33, 2),  'Last', fill=GRAY,  font=FONT)
        draw.text((33, 10), c1,     fill=WHITE, font=FONT)
        draw.text((33, 18), c2,     fill=WHITE, font=FONT)
        # Scores right-aligned
        bb_s1 = draw.textbbox((0, 0), str(s1), font=FONT)
        bb_s2 = draw.textbbox((0, 0), str(s2), font=FONT)
        draw.text((62 - (bb_s1[2]-bb_s1[0]), 10), str(s1), fill=GOLD, font=FONT)
        draw.text((62 - (bb_s2[2]-bb_s2[0]), 18), str(s2), fill=GOLD, font=FONT)
    else:
        draw.text((33, 12), 'No data', fill=GRAY, font=FONT)

    return img

# ── Main loop ─────────────────────────────────────────────────────────────────

while True:
    check_and_show_notification(matrix, canvas)

    with lock:
        ng = state.get('next_game')

    img    = draw_game_frame(ng) if ng else draw_no_game_frame()
    canvas.SetImage(img)
    canvas = matrix.SwapOnVSync(canvas)
    time.sleep(0.04)
