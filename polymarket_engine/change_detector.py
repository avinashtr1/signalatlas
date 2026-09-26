import json
from pathlib import Path

FEED = Path("analytics/intelligence_feed.json")
PREV = Path("analytics/intelligence_feed_prev.json")

def load(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def save(p,data):
    p.write_text(json.dumps(data,indent=2))

def main():
    current = load(FEED)
    prev = load(PREV)

    if current == prev:
        print("NO_CHANGE")
        return

    save(PREV,current)
    print("CHANGE_DETECTED")

if __name__ == "__main__":
    main()
