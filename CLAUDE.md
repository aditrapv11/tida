# Tidabit — DIY Tidbyt Clone

## Hardware

| Component | Details |
|---|---|
| SBC | Raspberry Pi Zero 2 W Rev 1.0 |
| Display | 64×32 RGB LED matrix, P3 pitch, HUB75 interface |
| HAT | Adafruit RGB Matrix Bonnet (#3211) — seated on Pi GPIO, no soldering |
| Power | 5V 4A barrel jack → Bonnet → panel |
| Storage | SanDisk 32GB Ultra A1 microSD |
| WiFi | 2.4GHz only (Pi Zero 2 W limitation — critical) |

## Connections
- Bonnet seated on Pi 40-pin GPIO header
- Gray HUB75 ribbon cable: panel INPUT port → Bonnet HUB75 port
- White power connector: panel VCC/GND port
- Red/black spade connectors: Bonnet screw terminal

## Pi Credentials
- Hostname: \`raspberrypi-tidabit\`
- Username: \`tidabit1977\`
- LAN IP: \`10.0.0.134\`
- Tailscale IP: \`100.91.141.121\`
- Tailscale DNS: \`raspberrypi-tidabit.taild7f614.ts.net\`
- Public HTTPS (Tailscale Funnel): \`https://raspberrypi-tidabit.taild7f614.ts.net\` → proxies :5001
- SSH: \`ssh tidabit1977@10.0.0.134\` (key auth, no password)
- OS: Raspberry Pi OS Lite (64-bit), Python 3.13.5

## Architecture

Three long-running systemd services manage everything — do NOT run display scripts manually with sudo.

| Service | What it does | User |
|---|---|---|
| \`display-controller.service\` | Flask control API on **:5001** (iPhone UI, /show, /brightness, /alexa/show/<name>) | root |
| \`tidabit-display.service\` | Runs \`cycle.py\` which spawns the current app per \`tidabit_settings.json\` | root |
| \`tidabit-notify.service\` | Flask notification server on **:5000**, writes \`/tmp/claude_notify\` flag | tidabit1977 |

Switch apps via the controller API, which \`pkill\`s the old script and \`Popen\`s the new one:
\`\`\`bash
curl http://10.0.0.134:5001/show/weather   # redirects to iPhone UI
# or POST /alexa/show/<name> for the authenticated remote path
\`\`\`

\`cycle.py\` is the default "app" (key=\`cycle\`) that rotates through entries in \`tidabit_settings.json\`. Selecting any other app stops the cycle until you switch to \`cycle\` again.

## Display scripts (\`~/*.py\`)

| File | Key | Description |
|---|---|---|
| \`controller.py\` | — | Flask on :5001 (control plane, not a display app) |
| \`cycle.py\` | \`cycle\` | Rotates through apps from \`tidabit_settings.json\` |
| \`notification_server.py\` | — | Flask on :5000 (Claude Code notifications) |
| \`notify.py\` | — | Shared notification overlay module (space-invader shower). Called from every display app's main loop. |
| \`hello_world.py\` | — | "Hello World" scroll (legacy, not in cycle) |
| \`earth.py\` | \`earth\` | Spinning Earth + ISS orbit |
| \`mbta.py\` | \`mbta\` | MBTA Red Line arrivals at Central Square |
| \`weather.py\` | \`weather\` | Weather display (api.weather.gov, no key needed) |
| \`spotify.py\` | \`spotify\` | Now-playing (uses \`spotify_tokens.json\`) |
| \`formlabs.py\` | \`formlabs\` | Formlabs butterfly (rendered from \`butterfly_sprite.png\`) |
| \`girl.py\` | \`maya\` | Portrait (note: key→file mapping in controller.py, \`maya\` → \`girl.py\`) |
| \`sentry.py\` | \`sentry\` | Static sentry icon |
| \`timer.py\` | — | Countdown timer (launched via /timer/start/<secs>) |
| \`cooking.py\` | — | Recipe stepper (launched via /cooking/*) |
| \`gen_butterfly.py\` | — | One-shot: generates \`butterfly_sprite.png\` |

## Controller.py endpoints (Flask on :5001)

- \`GET /\` — iPhone web UI (access at http://10.0.0.134:5001/)
- \`GET /show/<name>\` — switch apps (redirects to /)
- \`GET /current\` — \`{app, brightness}\` JSON
- \`GET /brightness/<10-100>\` — set brightness (persists to \`tidabit_settings.json\`)
- \`GET /timer/start/<seconds>\` — launches timer.py
- \`POST /settings/cycle\` — update \`cycle\` list
- \`GET /shutdown\`, \`GET /reboot\` — power control (LAN-only)
- \`GET /cooking/*\` — recipe UI endpoints
- \`POST /alexa/show/<name>\` — token-gated endpoint for the Alexa skill (see below)

### Funnel guard (internet exposure)

Tailscale Funnel exposes :5001 publicly over HTTPS. The \`@app.before_request _guard_funnel_traffic\` hook in controller.py checks the \`Tailscale-Funnel-Request\` header:
- If present and path is NOT \`/alexa/*\` → return 403
- If present and path IS \`/alexa/*\` → require \`X-Auth-Token\` header matching \`TIDABIT_ALEXA_TOKEN\` env var

Token lives in \`/etc/tidabit-alexa.env\` (root-owned, mode 600), loaded via systemd \`EnvironmentFile=\`.

## Alexa skill integration

Custom Alexa skill (invocation: \`pixel board\`) hosted on Alexa-hosted Python Lambda. Lambda calls \`POST https://<pi>.<tailnet>.ts.net/alexa/show/<name>\` with \`X-Auth-Token\`. Voice: *"Alexa, tell pixel board to show weather"* or dialog-mode *"Alexa, open pixel board"* then bare app name.

Skill artifacts on Mac/Windows at \`~/Desktop/Claude_Projects/tidabit-alexa/\` (not on Pi).

## Settings file

\`~/tidabit_settings.json\`:
\`\`\`json
{
  "brightness": 100,
  "cycle": [
    {"key": "spotify", "active": true, "duration": 90},
    {"key": "earth",   "active": true, "duration": 60},
    ...
  ]
}
\`\`\`
Edited via the iPhone UI or POST /settings/cycle. Changes take effect on the next cycle tick.

## External APIs

- **MBTA:** key \`37ad2966559e4902af8d13a2c5c8cd8d\`, stop \`place-cntsq\` (Central Square Red Line). Polls every 30s, falls back to schedules if no live predictions.
- **Weather:** api.weather.gov (no key).
- **Spotify:** tokens in \`~/spotify_tokens.json\` (OAuth, refreshed automatically).

## Software Stack
- \`rgbmatrix\` — real LED panel driver (hzeller/rpi-rgb-led-matrix, installed system-wide)
- \`RGBMatrixEmulator\` — browser preview on port 8888 (installed system-wide)
- \`Pillow\` — image/text rendering
- \`Flask\` — web/API layer
- \`rgbmatrix\` options always use \`hardware_mapping = 'adafruit-hat'\`

## Imports (use this pattern in all display scripts)
\`\`\`python
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
\`\`\`

## Operating tips

- To try a display change: \`sudo systemctl restart display-controller\` (reloads controller.py)
- To manually pick an app: \`curl http://127.0.0.1:5001/show/earth\`
- To debug an app: stop the cycle (\`curl .../show/earth\`), then tail journalctl
- \`sudo journalctl -u display-controller -f\` for controller logs
- \`sudo journalctl -u tidabit-display -f\` for the cycle + whatever app it's running
- Never run \`sudo python3 ~/earth.py\` manually; it will conflict with the service

## Hardware notes
- Adafruit Matrix Bonnet does NOT support Pi 5 — reason Zero 2 W was chosen
- isolcpus=3 can be added to /boot/cmdline.txt for slightly smoother display
- Swap file at /swapfile (512MB) was needed to compile rgbmatrix Python bindings

## Owner context
- Jorge Partida, Formlabs FP&A
- Mac source files at \`~/Desktop/tidabit-project/\`; Windows at \`~/Desktop/Claude_Projects/tidabit-alexa/\` (Alexa skill)
- Previous \`CLAUDE.md\` backed up as \`CLAUDE.md.bak\`
