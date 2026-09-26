import os
import requests
from pathlib import Path

FILE = Path("analytics/intelligence_feed_v2.txt")

def main():
    token = os.getenv("TG_BOT_TOKEN", "").strip()
    chat = os.getenv("TG_PRO_CHAT_ID", "").strip()

    if not token or not chat:
        print("pro telegram env vars missing")
        return

    if not FILE.exists():
        print("feed v2 missing")
        return

    text = FILE.read_text(encoding="utf-8")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    r = requests.post(
        url,
        json={
            "chat_id": chat,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=15,
    )

    print("PRO FEED V2 SENT")
    print(r.status_code)
    print(r.text)

if __name__ == "__main__":
    main()
