"""
Lightweight Flask server that receives POST /notify from Claude Code hooks
and writes a flag file that display scripts pick up.

Run as a systemd service (no sudo needed).
"""
from flask import Flask, jsonify

FLAG_FILE = "/tmp/claude_notify"

app = Flask(__name__)

@app.route("/notify", methods=["POST"])
def notify():
    import time
    with open(FLAG_FILE, "w") as f:
        f.write(str(time.time()))
    return jsonify({"status": "ok"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
