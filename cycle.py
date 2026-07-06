#!/usr/bin/env python3
"""
cycle.py — Rotates through display apps.
App list and per-app durations are read live from tidabit_settings.json each iteration.
"""
import json
import os
import subprocess
import time
from pathlib import Path

NOTIFY_FLAG     = '/tmp/claude_notify'
BRIGHTNESS_FILE = '/tmp/tidabit_brightness'
SETTINGS_FILE   = '/home/tidabit1977/tidabit_settings.json'

DEFAULT_CYCLE = [
    {'key': 'spotify', 'active': True,  'duration': 90},
    {'key': 'earth',   'active': True,  'duration': 90},
    {'key': 'weather', 'active': True,  'duration': 90},
]


def load_cycle():
    try:
        s          = json.loads(Path(SETTINGS_FILE).read_text())
        brightness = s.get('brightness', 80)
        Path(BRIGHTNESS_FILE).write_text(str(brightness))
        active = [(e['key'], e['duration']) for e in s.get('cycle', []) if e.get('active')]
        return active if active else [(e['key'], e['duration']) for e in DEFAULT_CYCLE]
    except Exception:
        return [(e['key'], e['duration']) for e in DEFAULT_CYCLE]


def main():
    idx = 0
    while True:
        entries = load_cycle()
        if not entries:
            time.sleep(5)
            continue

        key, duration = entries[idx % len(entries)]
        script = f'/home/tidabit1977/{key}.py'

        try:
            os.remove(NOTIFY_FLAG)
        except FileNotFoundError:
            pass

        print(f'[cycle] {key} for {duration}s', flush=True)
        proc = subprocess.Popen(['python3', script])
        time.sleep(duration)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        idx += 1


if __name__ == '__main__':
    main()
