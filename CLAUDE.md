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
- Hostname: `raspberrypi-tidabit`
- Username: `tidabit1977`
- IP: `10.0.0.134`
- SSH: `ssh tidabit1977@10.0.0.134` (key auth, no password)
- OS: Raspberry Pi OS Lite (64-bit), Python 3.13.5

## Running Apps
All display scripts require `sudo` to access GPIO:
```bash
sudo python3 ~/mbta.py
sudo python3 ~/earth.py
sudo python3 ~/hello_world.py
```

To kill any running script:
```bash
pkill -f python3
```

## Software Stack
- `rgbmatrix` — real LED panel driver (hzeller/rpi-rgb-led-matrix, installed system-wide)
- `RGBMatrixEmulator` — browser preview on port 8888 (installed system-wide)
- `Pillow` — image/text rendering
- `rgbmatrix` options always use `hardware_mapping = 'adafruit-hat'`

## Imports (use this pattern in all scripts)
```python
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
```

## Display Scripts
| File | Description |
|---|---|
| `~/hello_world.py` | Scrolling "Hello World" text |
| `~/earth.py` | Spinning Earth with ISS orbit animation |
| `~/mbta.py` | Live MBTA Red Line arrivals at Central Square |
| `~/weather.py` | Weather display (api.weather.gov, no key needed) |
| `~/girl.py` | Pixel art girl — brown hair, blue eyes, blue/white striped shirt, Boston skyline background, eyes scan left/right every 3s |
| `~/formlabs.py` | Formlabs butterfly logo revolving on vertical axis, Formlabs blue + orange twinkling stars, crisp 3×5 pixel clock (bottom-right), light green shooting star triplets every 20 min |
| `~/spotify.py` | Spotify now-playing — album art, scrolling title, artist, progress bar. Toggle `UI_V2` for alternate layout (smaller art, larger text). Tokens at `/etc/spotify_tokens.json` |
| `~/cycle.py` | Rotates through `earth.py → weather.py → mbta.py` in 60s increments (run via systemd) |

## MBTA API
- Key: `37ad2966559e4902af8d13a2c5c8cd8d`
- Stop ID: `place-cntsq` (Central Square Red Line)
- Direction 0 = Ashmont/Braintree, Direction 1 = Alewife
- Polls every 30 seconds, falls back to schedules if no live predictions

## Project Files on Mac
- `~/Desktop/tidabit-project/` — all source files
- `~/Desktop/PersonalClaudeProjects/MBTA_Tracker/` — existing React MBTA app (source of API key)

## Claude Code Notification System

When Claude Code finishes a response, a `Stop` hook in `~/.claude/settings.json` fires:
```
curl -s -X POST http://10.0.0.134:5000/notify || true
```

### Pi-side components
| File | Description |
|---|---|
| `~/notification_server.py` | Flask server on port 5000 — receives POST `/notify`, writes timestamp to `/tmp/claude_notify` |
| `~/notify.py` | Shared module imported by display scripts — checks flag file and runs space-invader-shower animation |

### Triggers
- `Stop` — fires when Claude finishes a response
- `Notification` — fires when Claude needs user input/attention (confirmations, input prompts)

### How it works
1. `notification_server.py` runs as a systemd service (no sudo) on the Pi
2. On `POST /notify`, it writes `time.time()` to `/tmp/claude_notify`
3. Each display script calls `check_and_show_notification(matrix, canvas)` in its main loop
4. If the flag is fresh (< 8s old) and cooldown (10s) has passed, a 7-second space invader animation plays over the current display

### Starting the server
```bash
python3 ~/notification_server.py
# or via systemd: sudo systemctl start notification-server
```

## Cycle / Autostart
- `tidabit-display` systemd service runs `cycle.py` on boot
- Manage: `sudo systemctl stop|start|restart tidabit-display`
- Stop the cycle to run a single script manually; restart to resume rotation
- `cycle.py` clears `/tmp/claude_notify` before each app launch to prevent stale notifications

## formlabs.py Details
- Butterfly sprite rendered from SVG (`butterfly_logo.svg`) via cairosvg at 8× then downscaled with LANCZOS
- Sprite regeneration script: `~/gen_butterfly.py`
- Revolution uses triangular wave + power curve (`L * |L|^0.4`) for constant apparent speed with no pause at face-on
- Back face dimmed (45–100% brightness) to make rotation read as continuous
- Clock: `time.strftime("%-I:%M")` from Pi system clock, rendered as hardcoded 3×5 pixel font
- Shooting stars: 3 diverging streaks, randomized from 3 path variants, every 20 min

## Display Controller

Web UI to switch apps from iPhone — `http://10.0.0.134:5001`

- Runs as `display-controller` systemd service (User=root, port 5001)
- Source: `~/controller.py`
- Detects currently running app via `pgrep`, kills it, launches the new one
- Add to iPhone home screen: Safari → Share → "Add to Home Screen"
- Manage: `sudo systemctl stop|start|restart display-controller`

## Next Steps
- [ ] Add `spotify.py`, `formlabs.py`, and `girl.py` to the cycle rotation
- [ ] 3D print enclosure on Formlabs SLS printer (Jorge works at Formlabs)

## spotify.py Details
- Two layouts: `UI_V2 = False` (32×32 art) / `UI_V2 = True` (26×26 art, 2px left margin, vertically centered, wider text panel)
- Title scrolls at 18px/sec when wider than panel; artist truncated (3×5 font)
- Progress bar in Spotify green; elapsed time right-aligned
- Title strip and artist text pre-rendered once per track change (no per-frame putpixel — avoids PWM flicker)
- Spotify audio-features endpoint (`/audio-features`) returns 403 for this app — Spotify deprecated it for new apps in late 2024
- Token refresh handled automatically; tokens stored at `/etc/spotify_tokens.json` (644) to avoid home-dir permission issues
- Re-authorize: run `spotify_auth.py` on Mac, scp new `spotify_tokens.json` to `/etc/spotify_tokens.json`

## RGB Matrix Performance Notes
- All scripts use `pwm_bits = 7` (down from default 11) — reduces flicker on dense/photographic images
- `SwapOnVSync` return value must be reassigned: `canvas = matrix.SwapOnVSync(canvas)` — without this, tearing occurs on complex images
- Dense photographic content (album art, gradients) flickers more than sparse content — hardware limitation of budget HUB75 panels
- Further tuning options if needed: `pwm_bits = 5`, `limit_refresh_rate_hz = 100`, `brightness = 60`

## Notes
- Adafruit Matrix Bonnet does NOT support Pi 5 — reason Zero 2 W was chosen
- `isolcpus=3` active in `/boot/firmware/cmdline.txt` for smoother PWM timing
- Swap file at /swapfile (512MB) was needed to compile rgbmatrix Python bindings
- `cairosvg` + `libcairo2` installed on Pi for SVG rendering
