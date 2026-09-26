import hashlib
import os
from pathlib import Path
from polymarket_engine.utils.channel_sender import send as send_channel

FEED_PATH = Path("analytics/alpha_feed.txt")
STATE_DIR = Path("analytics/.state")
LAST_HASH_PATH = STATE_DIR / "last_alpha_feed_hash.txt"

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    send_tg = os.getenv("ALPHA_SEND_TG", "0") == "1"
    force_send = os.getenv("ALPHA_FORCE_SEND", "0") == "1"

    if not FEED_PATH.exists():
        print("alpha feed file not found")
        return

    text = FEED_PATH.read_text(encoding="utf-8").strip()
    if not text:
        print("alpha feed is empty")
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    new_hash = sha256_text(text)
    old_hash = LAST_HASH_PATH.read_text(encoding="utf-8").strip() if LAST_HASH_PATH.exists() else ""

    if not force_send and new_hash == old_hash:
        print("alpha feed unchanged: skip send")
        return

    if not send_tg:
        print("ALPHA_SEND_TG=0: dry run, not sending")
        return

    ok = send_channel("alpha_feed", text)
    print("alpha feed sent:", ok)

    if ok:
        LAST_HASH_PATH.write_text(new_hash, encoding="utf-8")

if __name__ == "__main__":
    main()
