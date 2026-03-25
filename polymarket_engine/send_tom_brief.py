import hashlib
import os
from pathlib import Path
from polymarket_engine.utils.telegram_notifier import TelegramNotifier

OPS_BRIEF = Path("analytics/executive_brief.txt")
STATE_DIR = Path("analytics/.state")
LAST_HASH_PATH = STATE_DIR / "last_tom_brief_hash.txt"

def run_cmd(path):
    import subprocess
    res = subprocess.run(
        [path],
        cwd="/root/.openclaw/workspace",
        capture_output=True,
        text=True,
        check=False,
    )
    return (res.stdout or "").strip()

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    send_tg = os.getenv("TOM_SEND_TG", "0") == "1"
    force_send = os.getenv("TOM_FORCE_SEND", "0") == "1"

    parts = []

    if OPS_BRIEF.exists():
        parts.append(OPS_BRIEF.read_text(encoding="utf-8").strip())
    else:
        parts.append("SIGNALATLAS EXECUTIVE BRIEF\n\nNot available.")

    deploy_now = run_cmd("/root/.openclaw/workspace/tom_deploy_now.sh")
    if deploy_now:
        parts.append("DEPLOY NOW\n" + deploy_now)

    top_quality = run_cmd("/root/.openclaw/workspace/tom_top_quality.sh")
    if top_quality:
        parts.append("TOP QUALITY\n" + top_quality)

    text = "\n\n".join(parts).strip()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    new_hash = sha256_text(text)
    old_hash = LAST_HASH_PATH.read_text(encoding="utf-8").strip() if LAST_HASH_PATH.exists() else ""

    if not force_send and new_hash == old_hash:
        print("tom brief unchanged: skip send")
        return

    if not send_tg:
        print("TOM_SEND_TG=0: dry run, not sending")
        return

    tg = TelegramNotifier()
    ok = tg.send(text)
    print("tom brief sent:", ok)

    if ok:
        LAST_HASH_PATH.write_text(new_hash, encoding="utf-8")

if __name__ == "__main__":
    main()
