#!/usr/bin/env python3
"""
telegram_bridge.py — Push MT2 attack results to Telegram via Hermes gateway.
Hermes agent reads /sdcard/MT2/.telegram_outbox.jsonl and forwards to user.
"""
import json, time, os
from pathlib import Path

OUTBOX = Path("/sdcard/MT2/.telegram_outbox.jsonl")

def send(kind, message):
    """Append a message to outbox for Hermes to forward."""
    entry = {
        "ts": int(time.time()),
        "kind": kind,  # 'attack', 'cred', 'handshake', 'status'
        "message": message
    }
    with open(OUTBOX, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[TG:{kind}] {message}", flush=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        send(sys.argv[1], " ".join(sys.argv[2:]))
    else:
        print("usage: telegram_bridge.py <kind> <message>")
