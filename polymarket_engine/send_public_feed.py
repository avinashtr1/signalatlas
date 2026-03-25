import os
import requests
from pathlib import Path

FILE = Path("analytics/intelligence_feed_public.txt")

def main():
    token = os.getenv("TG_BOT_TOKEN", "").strip()
    chat = os.getenv("TG_PUBLIC_CHAT_ID", "").strip()

    if not token or not chat:
        print("public telegram env vars missing")
        return

    if not FILE.exists():
        print("feed missing")
        return

    text = FILE.read_text(encoding="utf-8")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        r = requests.post(
            url,
            json={
                "chat_id": chat,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        print("PUBLIC FEED SENT")
        print(r.status_code)
        print(r.text)
    except Exception as e:
        print("PUBLIC FEED FAILED")
        print(str(e))

if __name__ == "__main__":
    main()
