import hashlib
import os
import urllib.request
from pathlib import Path
from polymarket_engine.utils.telegram_notifier import TelegramNotifier

STATE_DIR = Path("analytics/.state")
LAST_HASH_PATH = STATE_DIR / "last_tom_card_hash.txt"

API_BASE = os.getenv("SIGNALATLAS_API_BASE", "http://127.0.0.1:8011").rstrip("/")
API_KEY = os.getenv("SIGNALATLAS_API_KEY", "").strip()

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def fetch_text(path: str) -> str:
    req = urllib.request.Request(
        API_BASE + path,
        headers={"X-API-Key": API_KEY} if API_KEY else {},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")

def main():
    send_tg = os.getenv("TOM_SEND_TG", "0") == "1"
    force_send = os.getenv("TOM_FORCE_SEND", "0") == "1"

    text = fetch_text("/api/tom-card").strip()
    if not text:
        print("tom card empty")
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    new_hash = sha256_text(text)
    old_hash = LAST_HASH_PATH.read_text(encoding="utf-8").strip() if LAST_HASH_PATH.exists() else ""

    if not force_send and new_hash == old_hash:
        print("tom card unchanged: skip send")
        return

    if not send_tg:
        print("TOM_SEND_TG=0: dry run, not sending")
        return

    tg = TelegramNotifier()
    ok = tg.send(text)
    print("tom card sent:", ok)

    if ok:
        LAST_HASH_PATH.write_text(new_hash, encoding="utf-8")

if __name__ == "__main__":
    main()
