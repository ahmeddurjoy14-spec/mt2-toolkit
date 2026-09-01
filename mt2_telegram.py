#!/usr/bin/env python3
"""
mt2_telegram.py — Sends MT2 attack updates to you via Hermes gateway.
Hermes receives these via a custom hook, and forwards to your Telegram.
"""
import sys, json, time
from pathlib import Path

MSG_FILE = Path("/sdcard/MT2/.telegram_outbox.jsonl")

def emit(kind, payload):
    """Append a message to outbox; Hermes picks it up."""
    msg = {
        "ts": int(time.time()),
        "kind": kind,
        "payload": payload
    }
    with open(MSG_FILE, "a") as f:
        f.write(json.dumps(msg) + "\n")
    print(f"[telegram] {kind}: {payload}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: mt2_telegram.py <kind> <msg>")
        sys.exit(0)
    kind = sys.argv[1]
    msg = " ".join(sys.argv[2:])
    emit(kind, msg)
