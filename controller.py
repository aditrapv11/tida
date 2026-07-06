#!/usr/bin/env python3
"""
controller.py — Web UI to switch Tidabit display apps.
Access from iPhone at http://10.0.0.134:5001
"""
import hmac
import json
import os
import subprocess
import time
from pathlib import Path
from flask import Flask, jsonify, redirect, Response, request

app = Flask(__name__)

SCRIPTS = [
    ('spotify',  'Spotify',  '🎵'),
    ('mbta',     'MBTA',     '🚇'),
    ('weather',  'Weather',  '🌤'),
    ('earth',    'Earth',    '🌍'),
    ('formlabs', 'Formlabs', '🦋'),
    ('maya',     'Maya',     '👩'),
    ('sentry',   'Sentry',   '🔴'),
    ('worldcup', 'World Cup', '⚽'),
    ('timer',    'Timer',    '⏱'),
    ('cooking',  'Cooking',  '🍳'),
    ('cycle',    'Cycle',    '🔄'),
]
SCRIPT_KEYS = [k for k, _, _ in SCRIPTS]
ALEXA_TOKEN = os.environ.get("TIDABIT_ALEXA_TOKEN", "")

@app.before_request
def _guard_funnel_traffic():
    # Tailscale Funnel exposes :5001 on the public internet. Allow only
    # /alexa/* with a valid shared token; block everything else from Funnel.
    if request.headers.get("Tailscale-Funnel-Request"):
        if not request.path.startswith("/alexa/"):
            return ("", 403)
        token = request.headers.get("X-Auth-Token", "")
        if not ALEXA_TOKEN or not hmac.compare_digest(token, ALEXA_TOKEN):
            return ("", 401)

BRIGHTNESS_FILE    = '/tmp/tidabit_brightness'
TIMER_FILE         = '/tmp/tidabit_timer'
COOKING_STATE_FILE = '/tmp/cooking_state.json'
SETTINGS_FILE      = '/home/tidabit1977/tidabit_settings.json'

COOKING_RECIPES = ['Carbonara', 'Stir Fry', 'Cookies', 'Beef Tacos']
COOKING_STEPS   = [5, 4, 5, 4]

CYCLE_APPS = [
    {'key': 'spotify',  'label': 'Spotify',  'icon': '🎵'},
    {'key': 'earth',    'label': 'Earth',    'icon': '🌍'},
    {'key': 'weather',  'label': 'Weather',  'icon': '🌤'},
    {'key': 'mbta',     'label': 'MBTA',     'icon': '🚇'},
    {'key': 'formlabs', 'label': 'Formlabs', 'icon': '🦋'},
    {'key': 'maya',     'label': 'Maya',     'icon': '👩'},
    {'key': 'sentry',   'label': 'Sentry',   'icon': '🔴'},
    {'key': 'worldcup', 'label': 'World Cup', 'icon': '⚽'},
]

DEFAULT_SETTINGS = {
    'brightness': 80,
    'cycle': [
        {'key': 'spotify',  'active': True,  'duration': 90},
        {'key': 'earth',    'active': True,  'duration': 90},
        {'key': 'weather',  'active': True,  'duration': 90},
        {'key': 'mbta',     'active': False, 'duration': 90},
        {'key': 'formlabs', 'active': False, 'duration': 90},
        {'key': 'maya',     'active': False, 'duration': 90},
        {'key': 'sentry',   'active': False, 'duration': 90},
        {'key': 'worldcup', 'active': False, 'duration': 90},
    ]
}


def load_settings():
    try:
        return json.loads(Path(SETTINGS_FILE).read_text())
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(s):
    Path(SETTINGS_FILE).write_text(json.dumps(s, indent=2))


def get_current():
    for key in SCRIPT_KEYS:
        r = subprocess.run(['pgrep', '-f', f'{key}\\.py'], capture_output=True)
        if r.returncode == 0:
            return key
    return None


def get_brightness():
    return load_settings().get('brightness', 80)


def switch_to(name):
    if name not in SCRIPT_KEYS:
        return False
    # Map 'maya' key back to girl.py filename
    filename = 'girl' if name == 'maya' else name
    for key in SCRIPT_KEYS:
        fname = 'girl' if key == 'maya' else key
        subprocess.run(['pkill', '-f', f'{fname}\\.py'], capture_output=True)
    time.sleep(1)
    subprocess.Popen(
        ['python3', f'/home/tidabit1977/{filename}.py'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


def _load_cooking():
    try:
        return json.loads(Path(COOKING_STATE_FILE).read_text())
    except Exception:
        return {'recipe_idx': 0, 'step_idx': 0, 'timer_running': False,
                'timer_end': None, 'timer_total': None}


def _save_cooking(state):
    Path(COOKING_STATE_FILE).write_text(json.dumps(state))


PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
  <meta name="apple-mobile-web-app-title" content="Tidabit">
  <title>Tidabit</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0a0a0a;
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      min-height: 100svh;
      padding: env(safe-area-inset-top,20px) env(safe-area-inset-right,16px)
               env(safe-area-inset-bottom,20px) env(safe-area-inset-left,16px);
    }}
    header {{ text-align: center; padding: 32px 0 6px; }}
    h1 {{ font-size: 20px; font-weight: 800; letter-spacing: 4px; color: #fff; }}
    .now {{
      font-size: 11px; color: #444; letter-spacing: 1.5px;
      text-transform: uppercase; margin-top: 4px;
    }}
    .now span {{ color: #0762C8; }}
    .grid {{
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 10px; margin-top: 28px;
    }}
    .btn {{
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; gap: 8px; background: #161616;
      border: 1.5px solid #222; border-radius: 20px; padding: 24px 12px;
      color: #999; font-size: 12px; font-weight: 600; letter-spacing: 0.5px;
      text-transform: uppercase; cursor: pointer;
      -webkit-tap-highlight-color: transparent;
      transition: transform 0.1s; user-select: none;
    }}
    .btn:active {{ transform: scale(0.95); }}
    .btn .icon {{ font-size: 30px; }}
    .btn.on {{
      background: #0762C8; border: 2px solid #fff; color: #fff;
      box-shadow: 0 0 0 1px #0762C8;
    }}
    .btn.wide {{ grid-column: 1 / -1; flex-direction: row; padding: 20px; gap: 14px; }}
    .btn.wide .icon {{ font-size: 24px; }}

    .settings-btn {{
      display: flex; align-items: center; justify-content: center; gap: 10px;
      width: 100%; margin-top: 12px; padding: 18px; background: #111;
      border: 1.5px solid #1e1e1e; border-radius: 20px; color: #555;
      font-size: 12px; font-weight: 700; letter-spacing: 1.5px;
      text-transform: uppercase; cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }}
    .settings-btn:active {{ opacity: 0.7; }}

    /* Modals */
    .modal-overlay {{
      display: none; pointer-events: none;
      position: fixed; inset: 0;
      background: rgba(0,0,0,0.75); z-index: 100;
      align-items: flex-end; justify-content: center;
    }}
    .modal-overlay.open {{ display: flex; pointer-events: auto; }}
    .modal-sheet {{
      background: #1a1a1a; border-radius: 24px 24px 0 0;
      padding: 24px 20px calc(env(safe-area-inset-bottom,20px) + 20px);
      width: 100%; max-width: 480px; max-height: 88svh; overflow-y: auto;
    }}
    .modal-title {{
      font-size: 13px; font-weight: 700; letter-spacing: 1.5px;
      color: #666; text-transform: uppercase; text-align: center;
      margin-bottom: 20px;
    }}
    .section-label {{
      font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
      color: #444; text-transform: uppercase; margin: 20px 0 10px;
    }}
    .section-label:first-of-type {{ margin-top: 0; }}

    /* Brightness */
    .brightness-label {{
      display: flex; justify-content: space-between;
      font-size: 11px; font-weight: 600; letter-spacing: 1px;
      color: #666; text-transform: uppercase; margin-bottom: 12px;
    }}
    .brightness-label span {{ color: #fff; }}
    input[type=range] {{
      -webkit-appearance: none; width: 100%; height: 4px;
      border-radius: 2px; background: #333; outline: none;
    }}
    input[type=range]::-webkit-slider-thumb {{
      -webkit-appearance: none; width: 22px; height: 22px;
      border-radius: 50%; background: #fff; cursor: pointer;
    }}

    /* Cycle rows */
    .cycle-row {{
      display: flex; align-items: center; gap: 10px;
      padding: 8px 0; border-bottom: 1px solid #222;
    }}
    .cycle-row:last-of-type {{ border-bottom: none; }}
    .cycle-toggle {{
      flex: 1; display: flex; align-items: center; gap: 8px;
      padding: 10px 12px; background: #222; border: 1.5px solid #2a2a2a;
      border-radius: 12px; color: #555; font-size: 12px; font-weight: 700;
      letter-spacing: 0.5px; cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }}
    .cycle-toggle.on {{ background: #0d2040; border-color: #0762C8; color: #fff; }}
    .cycle-toggle:active {{ opacity: 0.7; }}
    .duration-select {{
      background: #222; color: #aaa; border: 1.5px solid #2a2a2a;
      border-radius: 10px; padding: 8px 4px; font-size: 12px; font-weight: 700;
      -webkit-appearance: none; appearance: none; text-align: center; width: 66px;
    }}

    /* Shared buttons */
    .primary-btn {{
      width: 100%; padding: 16px; background: #0762C8; border: none;
      border-radius: 14px; color: #fff; font-size: 14px; font-weight: 700;
      letter-spacing: 1px; text-transform: uppercase; cursor: pointer;
      -webkit-tap-highlight-color: transparent; margin-bottom: 10px;
    }}
    .primary-btn:active {{ opacity: 0.75; }}
    .cancel-btn {{
      width: 100%; padding: 14px; background: transparent; border: none;
      color: #555; font-size: 13px; font-weight: 600; cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }}

    /* Power */
    .power-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .shutdown {{
      padding: 18px; background: #1a0000; border: 1.5px solid #330000;
      border-radius: 20px; color: #cc2222; font-size: 12px; font-weight: 700;
      letter-spacing: 1px; text-transform: uppercase; cursor: pointer;
      -webkit-tap-highlight-color: transparent; user-select: none;
    }}
    .shutdown:active {{ opacity: 0.7; }}
    .reboot {{
      padding: 18px; background: #0d1a00; border: 1.5px solid #1a3300;
      border-radius: 20px; color: #66aa22; font-size: 12px; font-weight: 700;
      letter-spacing: 1px; text-transform: uppercase; cursor: pointer;
      -webkit-tap-highlight-color: transparent; user-select: none;
    }}
    .reboot:active {{ opacity: 0.7; }}

    /* Timer modal */
    .timer-inputs {{
      display: flex; align-items: center; gap: 10px; margin-bottom: 20px;
    }}
    .timer-inputs select {{
      flex: 1; background: #2a2a2a; color: #fff; border: 1.5px solid #333;
      border-radius: 14px; padding: 12px 8px; font-size: 28px; font-weight: 700;
      text-align: center; -webkit-appearance: none; appearance: none;
    }}
    .timer-sep {{ font-size: 28px; font-weight: 700; color: #fff; }}

    /* Cooking modal */
    .recipe-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }}
    .recipe-btn {{
      padding: 12px 6px; background: #1e1e1e; border: 1.5px solid #2a2a2a;
      border-radius: 14px; color: #999; font-size: 12px; font-weight: 700;
      letter-spacing: 0.5px; cursor: pointer; -webkit-tap-highlight-color: transparent;
    }}
    .recipe-btn:active {{ opacity: 0.7; }}
    .recipe-btn.active {{ background: #0762C8; border-color: #fff; color: #fff; }}
    .cooking-info {{ text-align: center; margin-bottom: 14px; }}
    .cooking-step-line {{ font-size: 12px; color: #0ae8f0; font-weight: 600; margin-bottom: 4px; }}
    .cooking-timer-display {{ font-size: 32px; font-weight: 700; color: #aaa; letter-spacing: 2px; }}
    .cooking-timer-display.running {{ color: #32dc50; }}
    .cooking-timer-display.done    {{ color: #ff4040; }}
    .cooking-btn-row {{ display: grid; grid-template-columns: 1fr 1.4fr 1fr; gap: 8px; margin-bottom: 10px; }}
    .cooking-nav {{
      padding: 14px 8px; background: #1a1a1a; border: 1.5px solid #2a2a2a;
      border-radius: 14px; color: #888; font-size: 13px; font-weight: 700;
      cursor: pointer; -webkit-tap-highlight-color: transparent;
    }}
    .cooking-nav:active {{ opacity: 0.7; }}
    .cooking-nav:disabled {{ opacity: 0.3; pointer-events: none; }}
    .cooking-timer-btn {{
      padding: 14px; background: #0762C8; border: none; border-radius: 14px;
      color: #fff; font-size: 13px; font-weight: 700; cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }}
    .cooking-timer-btn:active {{ opacity: 0.75; }}
    .cooking-timer-btn:disabled {{
      background: #1a1a1a; border: 1.5px solid #2a2a2a;
      color: #3a3a3a; pointer-events: none;
    }}
  </style>
</head>
<body>
  <header>
    <h1>TIDABIT</h1>
    <p class="now">Showing&nbsp; <span>{current_label}</span></p>
  </header>

  <div class="grid">
    {buttons}
  </div>

  <button class="settings-btn" id="settingsOpenBtn">⚙️&nbsp;&nbsp;Settings</button>

  <!-- Settings Modal -->
  <div class="modal-overlay" id="settingsModal">
    <div class="modal-sheet">
      <div class="modal-title">Settings</div>

      <div class="section-label">Brightness</div>
      <div class="brightness-label">Level <span id="bval">{brightness}%</span></div>
      <input type="range" min="10" max="100" step="5" value="{brightness}" id="bslider">

      <div class="section-label">Cycle Apps</div>
      <div id="cycleRows"></div>
      <button class="primary-btn" id="saveCycleBtn" style="margin-top:14px">Save &amp; Apply</button>

      <div class="section-label">System</div>
      <div class="power-row">
        <button class="shutdown" id="shutdownBtn">⏻&nbsp; Shut Down</button>
        <button class="reboot"   id="rebootBtn">↺&nbsp; Restart</button>
      </div>

      <button class="cancel-btn" id="settingsCloseBtn">Done</button>
    </div>
  </div>

  <!-- Cooking Modal -->
  <div class="modal-overlay" id="cookingModal">
    <div class="modal-sheet">
      <div class="modal-title">Cooking</div>
      <div class="recipe-grid" id="recipeGrid"></div>
      <div class="cooking-info">
        <div class="cooking-step-line"     id="cookingStepLine">—</div>
        <div class="cooking-timer-display" id="cookingTimerDisplay">--:--</div>
      </div>
      <div class="cooking-btn-row">
        <button class="cooking-nav"        id="cookingPrevBtn">◀ Back</button>
        <button class="cooking-timer-btn"  id="cookingTimerBtn">▶ Start</button>
        <button class="cooking-nav"        id="cookingNextBtn">Next ▶</button>
      </div>
      <button class="cancel-btn" id="cookingDoneBtn">Done</button>
    </div>
  </div>

  <!-- Timer Modal -->
  <div class="modal-overlay" id="timerModal">
    <div class="modal-sheet">
      <div class="modal-title">Set Timer</div>
      <div class="timer-inputs">
        <select id="tmins">{mins_options}</select>
        <span class="timer-sep">:</span>
        <select id="tsecs">{secs_options}</select>
      </div>
      <button class="primary-btn" id="timerStartBtn">Start</button>
      <button class="cancel-btn"  id="timerCancelBtn">Cancel</button>
    </div>
  </div>

  <script>
    // ── App grid ──────────────────────────────────────────────────────────────
    const timerModal = document.getElementById('timerModal');
    document.querySelectorAll('.btn[data-app]').forEach(b => {{
      b.addEventListener('click', () => {{
        if      (b.dataset.app === 'timer')   {{ timerModal.classList.add('open'); }}
        else if (b.dataset.app === 'cooking') {{ openCookingModal(); }}
        else {{ fetch('/show/' + b.dataset.app).then(() => location.reload()); }}
      }});
    }});

    // ── Timer modal ───────────────────────────────────────────────────────────
    document.getElementById('timerCancelBtn').addEventListener('click', () => {{
      timerModal.classList.remove('open');
    }});
    timerModal.addEventListener('click', e => {{
      if (e.target === timerModal) timerModal.classList.remove('open');
    }});
    document.getElementById('timerStartBtn').addEventListener('click', () => {{
      const m     = parseInt(document.getElementById('tmins').value);
      const s     = parseInt(document.getElementById('tsecs').value);
      const total = m * 60 + s;
      if (total <= 0) return;
      timerModal.classList.remove('open');
      fetch('/timer/start/' + total).then(() => location.reload());
    }});

    // ── Settings modal ────────────────────────────────────────────────────────
    const settingsModal = document.getElementById('settingsModal');
    const CYCLE_APPS    = {cycle_apps_json};
    let   cycleState    = {cycle_state_json};
    const DURATIONS     = [
      {{v:30,  l:'30s'}}, {{v:60,  l:'1 min'}}, {{v:90, l:'90s'}},
      {{v:120, l:'2 min'}},{{v:180, l:'3 min'}}, {{v:300, l:'5 min'}},
    ];

    function openSettingsModal() {{
      renderCycleRows();
      settingsModal.classList.add('open');
    }}

    function renderCycleRows() {{
      const container = document.getElementById('cycleRows');
      container.innerHTML = '';
      CYCLE_APPS.forEach(app => {{
        const entry = cycleState.find(e => e.key === app.key)
                      || {{key: app.key, active: false, duration: 90}};
        const row = document.createElement('div');
        row.className = 'cycle-row';

        const btn = document.createElement('button');
        btn.className   = 'cycle-toggle' + (entry.active ? ' on' : '');
        btn.innerHTML   = app.icon + ' ' + app.label;
        btn.dataset.key = app.key;
        btn.onclick     = () => {{
          entry.active = !entry.active;
          btn.classList.toggle('on', entry.active);
        }};

        const sel = document.createElement('select');
        sel.className   = 'duration-select';
        sel.dataset.key = app.key;
        DURATIONS.forEach(d => {{
          const opt = document.createElement('option');
          opt.value       = d.v;
          opt.textContent = d.l;
          if (d.v === entry.duration) opt.selected = true;
          sel.appendChild(opt);
        }});

        row.appendChild(btn);
        row.appendChild(sel);
        container.appendChild(row);
      }});
    }}

    document.getElementById('settingsOpenBtn').addEventListener('click', openSettingsModal);
    document.getElementById('settingsCloseBtn').addEventListener('click', () => {{
      settingsModal.classList.remove('open');
    }});
    settingsModal.addEventListener('click', e => {{
      if (e.target === settingsModal) settingsModal.classList.remove('open');
    }});

    document.getElementById('saveCycleBtn').addEventListener('click', () => {{
      const cycle = CYCLE_APPS.map(app => ({{
        key:      app.key,
        active:   document.querySelector('.cycle-toggle[data-key="' + app.key + '"]')
                    ?.classList.contains('on') ?? false,
        duration: parseInt(document.querySelector('.duration-select[data-key="' + app.key + '"]')?.value ?? 90),
      }}));
      fetch('/settings/cycle', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{cycle}}),
      }}).then(() => {{
        cycleState = cycle;
        const btn = document.getElementById('saveCycleBtn');
        btn.textContent = 'Saved \u2713';
        setTimeout(() => {{ btn.textContent = 'Save \u0026 Apply'; }}, 2000);
      }});
    }});

    // Brightness (live + persisted)
    const bslider = document.getElementById('bslider');
    const bval    = document.getElementById('bval');
    let bTimer;
    bslider.addEventListener('input', () => {{
      bval.textContent = bslider.value + '%';
      clearTimeout(bTimer);
      bTimer = setTimeout(() => {{ fetch('/brightness/' + bslider.value); }}, 400);
    }});

    // Power
    document.getElementById('shutdownBtn').addEventListener('click', () => {{
      if (confirm('Shut down Tidabit? Unplug and replug to restart.')) {{
        fetch('/shutdown').then(() => {{
          document.body.innerHTML = '<p style="color:#666;text-align:center;padding:40px;font-family:sans-serif">Shutting down\u2026</p>';
        }});
      }}
    }});
    document.getElementById('rebootBtn').addEventListener('click', () => {{
      if (confirm('Restart Tidabit? Will be back in ~30 seconds.')) {{
        fetch('/reboot').then(() => {{
          document.body.innerHTML = '<p style="color:#666;text-align:center;padding:40px;font-family:sans-serif">Restarting\u2026</p>';
        }});
      }}
    }});

    // ── Cooking ───────────────────────────────────────────────────────────────
    const cookingRecipeNames = ['Carbonara', 'Stir Fry', 'Cookies', 'Beef Tacos'];
    const cookingModal       = document.getElementById('cookingModal');
    let   cookingPollTimer   = null;

    function openCookingModal() {{
      cookingModal.classList.add('open');
      const grid = document.getElementById('recipeGrid');
      grid.innerHTML = '';
      cookingRecipeNames.forEach((name, i) => {{
        const b = document.createElement('button');
        b.className = 'recipe-btn'; b.textContent = name;
        b.onclick = () => cookingStartRecipe(i);
        grid.appendChild(b);
      }});
      cookingPollState();
      cookingPollTimer = setInterval(cookingPollState, 1000);
    }}

    function closeCookingModal() {{
      cookingModal.classList.remove('open');
      if (cookingPollTimer) {{ clearInterval(cookingPollTimer); cookingPollTimer = null; }}
    }}

    function cookingPollState() {{
      fetch('/cooking/state').then(r => r.json()).then(s => {{
        document.querySelectorAll('.recipe-btn').forEach((b, i) => {{
          b.classList.toggle('active', i === s.recipe_idx);
        }});
        document.getElementById('cookingStepLine').textContent =
          s.recipe_name + '  \u2022  Step ' + (s.step_idx + 1) + ' of ' + s.total_steps;
        const timerDiv = document.getElementById('cookingTimerDisplay');
        const timerBtn = document.getElementById('cookingTimerBtn');
        if (s.timer_total) {{
          const rem = (s.timer_remaining !== null && s.timer_remaining !== undefined)
                      ? s.timer_remaining : s.timer_total;
          const m = Math.floor(rem / 60), sec = rem % 60;
          timerDiv.textContent = m + ':' + String(sec).padStart(2, '0');
          timerDiv.className   = 'cooking-timer-display' +
                                 (s.timer_running ? ' running' : (rem <= 0 ? ' done' : ''));
          timerBtn.textContent = s.timer_running ? '\u23f8 Pause' : '\u25b6 Start';
          timerBtn.disabled    = false;
        }} else {{
          timerDiv.textContent = '--:--';
          timerDiv.className   = 'cooking-timer-display';
          timerBtn.textContent = 'No Timer';
          timerBtn.disabled    = true;
        }}
        document.getElementById('cookingPrevBtn').disabled = (s.step_idx === 0);
        document.getElementById('cookingNextBtn').disabled = (s.step_idx >= s.total_steps - 1);
      }});
    }}

    function cookingStartRecipe(idx) {{
      fetch('/cooking/start/' + idx).then(() => {{
        cookingPollState();
        setTimeout(() => location.reload(), 800);
      }});
    }}

    document.getElementById('cookingTimerBtn').addEventListener('click', () => {{
      fetch('/cooking/timer/toggle').then(() => cookingPollState());
    }});
    document.getElementById('cookingNextBtn').addEventListener('click', () => {{
      fetch('/cooking/next').then(() => cookingPollState());
    }});
    document.getElementById('cookingPrevBtn').addEventListener('click', () => {{
      fetch('/cooking/prev').then(() => cookingPollState());
    }});
    document.getElementById('cookingDoneBtn').addEventListener('click', closeCookingModal);
    cookingModal.addEventListener('click', e => {{
      if (e.target === cookingModal) closeCookingModal();
    }});
  </script>
</body>
</html>
"""


@app.route('/')
def index():
    current       = get_current()
    current_label = next((l for k, l, _ in SCRIPTS if k == current), '—')
    brightness    = get_brightness()
    settings      = load_settings()
    cycle_state   = settings.get('cycle', DEFAULT_SETTINGS['cycle'])

    buttons = ''
    for key, label, icon in SCRIPTS:
        on   = ' on'   if key == current else ''
        wide = ' wide' if key == 'cycle' else ''
        cls  = f'btn{on}{wide}'
        buttons += (
            f'<div class="{cls}" data-app="{key}">'
            f'<span class="icon">{icon}</span>{label}</div>\n'
        )
    mins_options     = '\n'.join(f'<option value="{i}">{i:02d}</option>' for i in range(100))
    secs_options     = '\n'.join(f'<option value="{i}">{i:02d}</option>' for i in range(60))
    cycle_apps_json  = json.dumps([{'key': a['key'], 'label': a['label'], 'icon': a['icon']}
                                   for a in CYCLE_APPS])
    cycle_state_json = json.dumps(cycle_state)

    return Response(
        PAGE.format(
            current_label=current_label,
            buttons=buttons,
            brightness=brightness,
            mins_options=mins_options,
            secs_options=secs_options,
            cycle_apps_json=cycle_apps_json,
            cycle_state_json=cycle_state_json,
        ),
        mimetype='text/html'
    )


@app.route('/show/<name>')
def show(name):
    switch_to(name)
    return redirect('/')


@app.route('/brightness/<int:val>')
def brightness(val):
    val = max(10, min(100, int(val)))
    Path(BRIGHTNESS_FILE).write_text(str(val))
    s = load_settings()
    s['brightness'] = val
    save_settings(s)
    current = get_current()
    if current:
        switch_to(current)
    return jsonify({'brightness': val})


@app.route('/timer/start/<int:seconds>')
def timer_start(seconds):
    seconds    = max(1, min(5999, seconds))
    press_time = time.time()
    for key in SCRIPT_KEYS:
        fname = 'girl' if key == 'maya' else key
        subprocess.run(['pkill', '-f', f'{fname}\\.py'], capture_output=True)
    subprocess.Popen(
        ['python3', '/home/tidabit1977/timer.py'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(0.5)
    end_ts = press_time + seconds
    Path(TIMER_FILE).write_text(json.dumps({'end': end_ts, 'total': seconds}))
    return redirect('/')


@app.route('/settings/cycle', methods=['POST'])
def settings_cycle():
    data = request.json
    if not data or 'cycle' not in data:
        return jsonify({'ok': False}), 400
    s = load_settings()
    s['cycle'] = data['cycle']
    save_settings(s)
    if get_current() == 'cycle':
        subprocess.Popen(['systemctl', 'restart', 'tidabit-display'])
    return jsonify({'ok': True})


@app.route('/shutdown')
def shutdown():
    subprocess.Popen(['shutdown', '-h', 'now'])
    return 'ok'


@app.route('/reboot')
def reboot():
    subprocess.Popen(['reboot'])
    return 'ok'


@app.route('/current')
def current():
    return jsonify({'app': get_current(), 'brightness': get_brightness()})


@app.route("/alexa/show/<name>", methods=["POST"])
def alexa_show(name):
    if not switch_to(name):
        return jsonify({"error": "unknown app"}), 404
    return jsonify({"status": "ok", "showing": name})


# ── Cooking routes ────────────────────────────────────────────────────────────

@app.route('/cooking/state')
def cooking_state():
    s    = _load_cooking()
    ridx = max(0, min(s.get('recipe_idx', 0), len(COOKING_RECIPES) - 1))
    sidx = s.get('step_idx', 0)
    rem  = None
    if s.get('timer_end'):
        rem = max(0, int(s['timer_end'] - time.time()))
    return jsonify({
        'recipe_idx':      ridx,
        'recipe_name':     COOKING_RECIPES[ridx],
        'step_idx':        sidx,
        'total_steps':     COOKING_STEPS[ridx],
        'timer_running':   s.get('timer_running', False),
        'timer_remaining': rem,
        'timer_total':     s.get('timer_total'),
    })


@app.route('/cooking/start/<int:n>')
def cooking_start(n):
    n = max(0, min(n, len(COOKING_RECIPES) - 1))
    _save_cooking({'recipe_idx': n, 'step_idx': 0,
                   'timer_running': False, 'timer_end': None, 'timer_total': None})
    switch_to('cooking')
    return jsonify({'ok': True})


@app.route('/cooking/next')
def cooking_next():
    s    = _load_cooking()
    ridx = max(0, min(s.get('recipe_idx', 0), len(COOKING_STEPS) - 1))
    sidx = s.get('step_idx', 0)
    if sidx < COOKING_STEPS[ridx] - 1:
        s['step_idx']      = sidx + 1
        s['timer_running'] = False
        s['timer_end']     = None
        _save_cooking(s)
    return jsonify({'ok': True, 'step_idx': s['step_idx']})


@app.route('/cooking/prev')
def cooking_prev():
    s    = _load_cooking()
    sidx = s.get('step_idx', 0)
    if sidx > 0:
        s['step_idx']      = sidx - 1
        s['timer_running'] = False
        s['timer_end']     = None
        _save_cooking(s)
    return jsonify({'ok': True, 'step_idx': s['step_idx']})


@app.route('/cooking/timer/toggle')
def cooking_timer_toggle():
    s = _load_cooking()
    if s.get('timer_running'):
        if s.get('timer_end'):
            s['timer_total'] = max(0, int(s['timer_end'] - time.time()))
        s['timer_running'] = False
        s['timer_end']     = None
    else:
        total = s.get('timer_total')
        if total and total > 0:
            s['timer_running'] = True
            s['timer_end']     = time.time() + total
    _save_cooking(s)
    return jsonify({'ok': True, 'running': s.get('timer_running', False)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
