import json
import os
from pathlib import Path
from datetime import datetime, timezone
import requests

SHOCK = Path("analytics/market_shocks.json")
STATE = Path("analytics/shock_alert_state.json")

BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TG_PUBLIC_CHAT_ID", "").strip()

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def save_json(p, data):
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def send(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("shock telegram env vars missing")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    print(r.status_code)
    print(r.text)

def main():
    doc = load_json(SHOCK)
    shocks = doc.get("shocks", [])
    state = load_json(STATE)
    sent = set(state.get("sent_keys", []))

    new_keys = set(sent)
    sent_now = 0

    for s in shocks[:10]:
        key = f"{s.get('market')}|{s.get('timestamp')}"
        if key in sent:
            continue

        msg = (
            "🚨 SIGNALATLAS MARKET SHOCK\n\n"
            f"Market: {s.get('market','unknown')}\n"
            f"Score: {s.get('score','n/a')}\n"
            f"Urgency: {s.get('urgency','n/a')}\n"
            f"Detected: {s.get('timestamp','n/a')}"
        )
        send(msg)
        new_keys.add(key)
        sent_now += 1

    save_json(STATE, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sent_keys": sorted(list(new_keys))[-500:]
    })

    if sent_now == 0:
        print("no shocks")
    else:
        print("shock alerts sent:", sent_now)

if __name__ == "__main__":
    main()
