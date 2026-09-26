
import hashlib
_DEDUP_CACHE = set()

def _dedupe(msg: str) -> bool:
    h = hashlib.sha256(msg.encode()).hexdigest()
    if h in _DEDUP_CACHE:
        return False
    _DEDUP_CACHE.add(h)
    if len(_DEDUP_CACHE) > 500:
        _DEDUP_CACHE.clear()
    return True

import json
import os
import urllib.parse
import urllib.request


class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("POLY_TG_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("POLY_TG_CHAT_ID", "").strip()
        self.enabled = bool(self.bot_token and self.chat_id)
        self._last_text = None

    def send(self, text: str):
        if not self.enabled:
            return False

        text = str(text)
        if text == self._last_text:
            return False
        self._last_text = text

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = urllib.parse.urlencode({
            "chat_id": self.chat_id,
            "text": text[:4000],
        }).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return bool(data.get("ok"))
