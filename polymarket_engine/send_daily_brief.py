import hashlib
import os
from pathlib import Path
from polymarket_engine.utils.telegram_notifier import TelegramNotifier

BRIEF_PATH = Path("analytics/daily_brief.txt")
STATE_DIR = Path("analytics/.state")
LAST_HASH_PATH = STATE_DIR / "last_daily_brief_hash.txt"

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    send_tg = os.getenv("SEND_TG", "0") == "1"
    force_send = os.getenv("FORCE_SEND", "0") == "1"

    if not BRIEF_PATH.exists():
        print("daily brief file not found")
        return

    text = BRIEF_PATH.read_text(encoding="utf-8").strip()
    if not text:
        print("daily brief is empty")
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    new_hash = sha256_text(text)
    old_hash = LAST_HASH_PATH.read_text(encoding="utf-8").strip() if LAST_HASH_PATH.exists() else ""

    if not force_send and new_hash == old_hash:
        print("daily brief unchanged: skip send")
        return

    if not send_tg:
        print("SEND_TG=0: dry run, not sending")
        return

    tg = TelegramNotifier()
    ok = tg.send(text)
    print("daily brief sent:", ok)

    if ok:
        LAST_HASH_PATH.write_text(new_hash, encoding="utf-8")

if __name__ == "__main__":
    main()
