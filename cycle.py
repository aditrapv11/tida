#!/usr/bin/env python3
"""
cycle.py — Rotates through display apps in 60-second increments.
Run via the tidabit-display systemd service (as root).
"""
import os
import subprocess
import time

NOTIFY_FLAG = "/tmp/claude_notify"

SCRIPTS = [
    "/home/tidabit1977/earth.py",
    "/home/tidabit1977/weather.py",
    "/home/tidabit1977/mbta.py",
]
INTERVAL = 60


def main():
    idx = 0
    while True:
        script = SCRIPTS[idx % len(SCRIPTS)]
        try:
            os.remove(NOTIFY_FLAG)
        except FileNotFoundError:
            pass
        print(f"[cycle] starting {script}", flush=True)
        proc = subprocess.Popen(["python3", script])
        time.sleep(INTERVAL)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        idx += 1


if __name__ == "__main__":
    main()
