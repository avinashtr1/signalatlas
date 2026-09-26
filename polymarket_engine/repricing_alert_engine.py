import json
import os
import requests
from pathlib import Path

SRC = Path("analytics/probability_repricing.json")

BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("TG_PRO_CHAT_ID", "").strip()

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def send(msg):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("repricing telegram env vars missing")
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
    data = load_json(SRC)
    rows = data.get("signals", [])

    if not rows:
        print("no repricing alerts")
        return

    for r in rows[:3]:
        msg = f"""⚡ SIGNALATLAS REPRICING ALERT

Market
{r.get('market_name', 'N/A')}

Previous Probability
{r.get('prev_probability')}

Current Probability
{r.get('curr_probability')}

Delta
{r.get('repricing_delta')}

Direction
{r.get('direction')}"""
        send(msg)

if __name__ == "__main__":
    main()
