import os
import requests
from pathlib import Path

FILE = Path("analytics/intelligence_feed_private.txt")

def main():
    token = os.getenv("TG_BOT_TOKEN")
    chat = os.getenv("TG_CHAT_ID")

    if not token or not chat:
        print("telegram env vars missing")
        return

    if not FILE.exists():
        print("feed missing")
        return

    text = FILE.read_text()

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    r = requests.post(url, json={
        "chat_id": chat,
        "text": text,
        "disable_web_page_preview": True
    })

    print("PRO FEED SENT")
    print(r.text)

if __name__ == "__main__":
    main()
