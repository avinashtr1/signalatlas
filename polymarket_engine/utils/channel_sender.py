import json
import os
from pathlib import Path
import requests

CONFIG_PATH = Path("polymarket_engine/channel_config.json")

def load_config():
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text())

def send(channel, text):
    cfg = load_config().get(channel)

    if not cfg:
        print(f"channel not configured: {channel}")
        return False

    token = os.getenv(cfg["bot_token_env"])
    chat = os.getenv(cfg["chat_id_env"])

    if not token or not chat:
        print("telegram env vars missing")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    r = requests.post(
        url,
        json={
            "chat_id": chat,
            "text": text
        },
        timeout=20
    )

    return r.status_code == 200
