import json
import os
import requests
from pathlib import Path

SHOCKS = Path("analytics/market_shocks.json")

BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("TG_PRO_CHAT_ID", "").strip()

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def send(msg):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("shock telegram env vars missing")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(
        url,
        json={
            "chat_id": CHANNEL_ID,
            "text": msg,
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    print(r.status_code)
    print(r.text)

def main():
    data = load_json(SHOCKS)
    shocks = data.get("shocks", [])

    if not shocks:
        print("no shocks")
        return

    for s in shocks[:3]:
        msg = f"""⚡ SIGNALATLAS SHOCK ALERT

Market
{s.get('market_name', 'N/A')}

Probability Move
{round(float(s.get('prob_move', 0.0) or 0.0), 3)}

Liquidity Drop
{round(float(s.get('liquidity_drop', 0.0) or 0.0), 3)}"""
        send(msg)

if __name__ == "__main__":
    main()
