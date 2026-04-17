#!/usr/bin/env python3
"""
controller.py — Web UI to switch Tidabit display apps.
Access from iPhone at http://10.0.0.134:5001
"""
import json
import subprocess
import time
from pathlib import Path
from flask import Flask, jsonify, redirect, Response

app = Flask(__name__)

SCRIPTS = [
    ('spotify',  'Spotify',  '🎵'),
    ('mbta',     'MBTA',     '🚇'),
    ('weather',  'Weather',  '🌤'),
    ('earth',    'Earth',    '🌍'),
    ('formlabs', 'Formlabs', '🦋'),
    ('girl',     'Girl',     '👩'),
    ('sentry',   'Sentry',   '🔴'),
    ('timer',    'Timer',    '⏱'),
    ('cooking',  'Cooking',  '🍳'),
    ('cycle',    'Cycle',    '🔄'),
]
SCRIPT_KEYS = [k for k, _, _ in SCRIPTS]

BRIGHTNESS_FILE    = '/tmp/tidabit_brightness'
TIMER_FILE         = '/tmp/tidabit_timer'
COOKING_STATE_FILE = '/tmp/cooking_state.json'
COOKING_RECIPES    = ['Carbonara', 'Stir Fry', 'Cookies', 'Beef Tacos']
COOKING_STEPS      = [5, 4, 5, 4]


def _load_cooking():
    try:
        return json.loads(Path(COOKING_STATE_FILE).read_text())
    except Exception:
        return {'recipe_idx': 0, 'step_idx': 0, 'timer_running': False,
                'timer_end': None, 'timer_total': None}


def _save_cooking(state):
    Path(COOKING_STATE_FILE).write_text(json.dumps(state))


def get_current():
    for key in SCRIPT_KEYS:
        r = subprocess.run(['pgrep', '-f', f'{key}\\.py'], capture_output=True)
        if r.returncode == 0:
            return key
    return None


def get_brightness():
    try:
        return int(Path(BRIGHTNESS_FILE).read_text().strip())
    except:
        return 80


def set_brightness(val):
    val = max(10, min(100, int(val)))
    Path(BRIGHTNESS_FILE).write_text(str(val))
    return val


def switch_to(name):
    if name not in SCRIPT_KEYS:
        return False
    for key in SCRIPT_KEYS:
        subprocess.run(['pkill', '-f', f'{key}\\.py'], capture_output=True)
    time.sleep(1)
    subprocess.Popen(
        ['python3', f'/home/tidabit1977/{name}.py'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


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
    header {{
      text-align: center;
      padding: 32px 0 6px;
    }}
    h1 {{
      font-size: 20px;
      font-weight: 800;
      letter-spacing: 4px;
      color: #fff;
    }}
    .now {{
      font-size: 11px;
      color: #444;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      margin-top: 4px;
    }}
    .now span {{ color: #0762C8; }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 28px;
    }}
    .btn {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      background: #161616;
      border: 1.5px solid #222;
      border-radius: 20px;
      padding: 24px 12px;
      color: #999;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
      transition: transform 0.1s;
      user-select: none;
    }}
    .btn:active {{ transform: scale(0.95); }}
    .btn .icon {{ font-size: 30px; }}
    .btn.on {{
      background: #0762C8;
      border: 2px solid #fff;
      color: #fff;
      box-shadow: 0 0 0 1px #0762C8;
    }}
    .btn.wide {{ grid-column: 1 / -1; flex-direction: row; padding: 20px; gap: 14px; }}
    .btn.wide .icon {{ font-size: 24px; }}

    /* Brightness */
    .brightness-section {{
      margin-top: 24px;
      padding: 20px;
      background: #161616;
      border: 1.5px solid #222;
      border-radius: 20px;
    }}
    .brightness-label {{
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 1px;
      color: #666;
      text-transform: uppercase;
      margin-bottom: 12px;
    }}
    .brightness-label span {{ color: #fff; }}
    input[type=range] {{
      -webkit-appearance: none;
      width: 100%;
      height: 4px;
      border-radius: 2px;
      background: #333;
      outline: none;
    }}
    input[type=range]::-webkit-slider-thumb {{
      -webkit-appearance: none;
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: #fff;
      cursor: pointer;
    }}

    /* Timer modal */
    .modal-overlay {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.75);
      z-index: 100;
      align-items: flex-end;
      justify-content: center;
    }}
    .modal-overlay.open {{ display: flex; }}
    .modal-sheet {{
      background: #1a1a1a;
      border-radius: 24px 24px 0 0;
      padding: 24px 20px calc(env(safe-area-inset-bottom,20px) + 20px);
      width: 100%;
      max-width: 480px;
    }}
    .modal-title {{
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 1.5px;
      color: #666;
      text-transform: uppercase;
      text-align: center;
      margin-bottom: 20px;
    }}
    .timer-inputs {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 20px;
    }}
    .timer-inputs select {{
      flex: 1;
      background: #2a2a2a;
      color: #fff;
      border: 1.5px solid #333;
      border-radius: 14px;
      padding: 12px 8px;
      font-size: 28px;
      font-weight: 700;
      text-align: center;
      -webkit-appearance: none;
      appearance: none;
    }}
    .timer-sep {{
      font-size: 28px;
      font-weight: 700;
      color: #fff;
    }}
    .timer-start {{
      width: 100%;
      padding: 16px;
      background: #0762C8;
      border: none;
      border-radius: 14px;
      color: #fff;
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
      margin-bottom: 10px;
    }}
    .timer-start:active {{ opacity: 0.75; }}
    .timer-cancel {{
      width: 100%;
      padding: 14px;
      background: transparent;
      border: none;
      color: #555;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }}

    /* Shutdown / Reboot */
    .power-row {{
      margin-top: 12px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }}
    .shutdown {{
      padding: 18px;
      background: #1a0000;
      border: 1.5px solid #330000;
      border-radius: 20px;
      color: #cc2222;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
    }}
    .shutdown:active {{ opacity: 0.7; }}
    .reboot {{
      padding: 18px;
      background: #0d1a00;
      border: 1.5px solid #1a3300;
      border-radius: 20px;
      color: #66aa22;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
    }}
    .reboot:active {{ opacity: 0.7; }}

    /* Cooking modal */
    .recipe-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 14px;
    }}
    .recipe-btn {{
      padding: 12px 6px;
      background: #1e1e1e;
      border: 1.5px solid #2a2a2a;
      border-radius: 14px;
      color: #999;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.5px;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }}
    .recipe-btn:active {{ opacity: 0.7; }}
    .recipe-btn.active {{
      background: #0762C8;
      border-color: #fff;
      color: #fff;
    }}
    .cooking-info {{
      text-align: center;
      margin-bottom: 14px;
    }}
    .cooking-step-line {{
      font-size: 12px;
      color: #0ae8f0;
      font-weight: 600;
      margin-bottom: 4px;
    }}
    .cooking-timer-display {{
      font-size: 32px;
      font-weight: 700;
      color: #aaa;
      letter-spacing: 2px;
    }}
    .cooking-timer-display.running {{ color: #32dc50; }}
    .cooking-timer-display.done    {{ color: #ff4040; }}
    .cooking-btn-row {{
      display: grid;
      grid-template-columns: 1fr 1.4fr 1fr;
      gap: 8px;
      margin-bottom: 10px;
    }}
    .cooking-nav {{
      padding: 14px 8px;
      background: #1a1a1a;
      border: 1.5px solid #2a2a2a;
      border-radius: 14px;
      color: #888;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }}
    .cooking-nav:active {{ opacity: 0.7; }}
    .cooking-nav:disabled {{ opacity: 0.3; pointer-events: none; }}
    .cooking-timer-btn {{
      padding: 14px;
      background: #0762C8;
      border: none;
      border-radius: 14px;
      color: #fff;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }}
    .cooking-timer-btn:active {{ opacity: 0.75; }}
    .cooking-timer-btn:disabled {{
      background: #1a1a1a;
      border: 1.5px solid #2a2a2a;
      color: #3a3a3a;
      pointer-events: none;
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

  <div class="brightness-section">
    <div class="brightness-label">Brightness <span id="bval">{brightness}%</span></div>
    <input type="range" min="10" max="100" step="5" value="{brightness}" id="bslider">
  </div>

  <div class="power-row">
    <button class="shutdown" id="shutdownBtn">⏻&nbsp; Shut Down</button>
    <button class="reboot"   id="rebootBtn">↺&nbsp; Restart</button>
  </div>

  <div class="modal-overlay" id="cookingModal">
    <div class="modal-sheet">
      <div class="modal-title">Cooking</div>
      <div class="recipe-grid" id="recipeGrid"></div>
      <div class="cooking-info">
        <div class="cooking-step-line"    id="cookingStepLine">—</div>
        <div class="cooking-timer-display" id="cookingTimerDisplay">--:--</div>
      </div>
      <div class="cooking-btn-row">
        <button class="cooking-nav"       id="cookingPrevBtn">◀ Back</button>
        <button class="cooking-timer-btn" id="cookingTimerBtn">▶ Start</button>
        <button class="cooking-nav"       id="cookingNextBtn">Next ▶</button>
      </div>
      <button class="timer-cancel" id="cookingDoneBtn">Done</button>
    </div>
  </div>

  <div class="modal-overlay" id="timerModal">
    <div class="modal-sheet">
      <div class="modal-title">Set Timer</div>
      <div class="timer-inputs">
        <select id="tmins">
          {mins_options}
        </select>
        <span class="timer-sep">:</span>
        <select id="tsecs">
          {secs_options}
        </select>
      </div>
      <button class="timer-start" id="timerStartBtn">Start</button>
      <button class="timer-cancel" id="timerCancelBtn">Cancel</button>
    </div>
  </div>

  <script>
    const modal = document.getElementById('timerModal');

    // App buttons — timer/cooking open modals, others switch directly
    document.querySelectorAll('.btn[data-app]').forEach(b => {{
      b.addEventListener('click', () => {{
        if (b.dataset.app === 'timer') {{
          modal.classList.add('open');
        }} else if (b.dataset.app === 'cooking') {{
          openCookingModal();
        }} else {{
          fetch('/show/' + b.dataset.app).then(() => location.reload());
        }}
      }});
    }});

    // Timer modal
    document.getElementById('timerCancelBtn').addEventListener('click', () => {{
      modal.classList.remove('open');
    }});
    modal.addEventListener('click', e => {{
      if (e.target === modal) modal.classList.remove('open');
    }});
    document.getElementById('timerStartBtn').addEventListener('click', () => {{
      const m = parseInt(document.getElementById('tmins').value);
      const s = parseInt(document.getElementById('tsecs').value);
      const total = m * 60 + s;
      if (total <= 0) return;
      modal.classList.remove('open');
      fetch('/timer/start/' + total).then(() => location.reload());
    }});

    // Brightness slider — debounced
    const slider = document.getElementById('bslider');
    const bval   = document.getElementById('bval');
    let bTimer;
    slider.addEventListener('input', () => {{
      bval.textContent = slider.value + '%';
      clearTimeout(bTimer);
      bTimer = setTimeout(() => {{
        fetch('/brightness/' + slider.value);
      }}, 400);
    }});

    // Shutdown
    document.getElementById('shutdownBtn').addEventListener('click', () => {{
      if (confirm('Shut down Tidabit?\\nUnplug and replug to restart.')) {{
        fetch('/shutdown').then(() => {{
          document.body.innerHTML = '<p style="color:#666;text-align:center;padding:40px;font-family:sans-serif">Shutting down…</p>';
        }});
      }}
    }});

    // Reboot
    document.getElementById('rebootBtn').addEventListener('click', () => {{
      if (confirm('Restart Tidabit?\\nWill be back in ~30 seconds.')) {{
        fetch('/reboot').then(() => {{
          document.body.innerHTML = '<p style="color:#666;text-align:center;padding:40px;font-family:sans-serif">Restarting…</p>';
        }});
      }}
    }});

    // ── Cooking ──────────────────────────────────────────────────────────────
    const cookingRecipeNames = ['Carbonara', 'Stir Fry', 'Cookies', 'Beef Tacos'];
    const cookingModal       = document.getElementById('cookingModal');
    let   cookingPollTimer   = null;

    function openCookingModal() {{
      cookingModal.classList.add('open');
      const grid = document.getElementById('recipeGrid');
      grid.innerHTML = '';
      cookingRecipeNames.forEach((name, i) => {{
        const b = document.createElement('button');
        b.className   = 'recipe-btn';
        b.textContent = name;
        b.onclick     = () => cookingStartRecipe(i);
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
      fetch('/cooking/state')
        .then(r => r.json())
        .then(s => {{
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
            const m   = Math.floor(rem / 60);
            const sec = rem % 60;
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
    current = get_current()
    current_label = next((l for k, l, _ in SCRIPTS if k == current), '—')
    brightness = get_brightness()
    buttons = ''
    for key, label, icon in SCRIPTS:
        on   = ' on'   if key == current else ''
        wide = ' wide' if key == 'cycle' else ''
        cls  = f'btn{on}{wide}'
        buttons += (
            f'<div class="{cls}" data-app="{key}">'
            f'<span class="icon">{icon}</span>{label}</div>\n'
        )
    mins_options = '\n'.join(f'<option value="{i}">{i:02d}</option>' for i in range(100))
    secs_options = '\n'.join(f'<option value="{i}">{i:02d}</option>' for i in range(60))
    return Response(
        PAGE.format(
            current_label=current_label,
            buttons=buttons,
            brightness=brightness,
            mins_options=mins_options,
            secs_options=secs_options,
        ),
        mimetype='text/html'
    )


@app.route('/show/<name>')
def show(name):
    switch_to(name)
    return redirect('/')


@app.route('/brightness/<int:val>')
def brightness(val):
    val = set_brightness(val)
    current = get_current()
    if current:
        switch_to(current)
    return jsonify({'brightness': val})


@app.route('/timer/start/<int:seconds>')
def timer_start(seconds):
    seconds    = max(1, min(5999, seconds))
    press_time = time.time()   # capture before any delay
    # Kill current script first so timer.py can grab the matrix
    for key in SCRIPT_KEYS:
        subprocess.run(['pkill', '-f', f'{key}\\.py'], capture_output=True)
    # timer.py launches with no timer file → shows cows immediately
    subprocess.Popen(
        ['python3', '/home/tidabit1977/timer.py'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Write the file after a short delay so the process is up and showing cows first
    time.sleep(0.5)
    end_ts = press_time + seconds   # anchored to press time, not post-sleep
    Path(TIMER_FILE).write_text(json.dumps({'end': end_ts, 'total': seconds}))
    return redirect('/')


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
        'recipe_idx':     ridx,
        'recipe_name':    COOKING_RECIPES[ridx],
        'step_idx':       sidx,
        'total_steps':    COOKING_STEPS[ridx],
        'timer_running':  s.get('timer_running', False),
        'timer_remaining': rem,
        'timer_total':    s.get('timer_total'),
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
