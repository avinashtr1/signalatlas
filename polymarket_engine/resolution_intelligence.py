import json
from pathlib import Path

BASE = Path("analytics")
LEDGER = BASE / "resolution_ledger.json"
OUT = BASE / "resolution_intelligence.json"

MODULES = [
    "vacuum",
    "microstructure",
    "stale_repricing",
    "resolution_arb",
    "collapse",
    "shock"
]

def load_rows():
    if not LEDGER.exists():
        return []
    data = json.loads(LEDGER.read_text())
    return data.get("rows", [])

def compute(rows):

    stats = {}

    for m in MODULES:
        stats[m] = {"wins":0,"total":0,"win_rate":0}

    for r in rows:

        if not isinstance(r, dict):
            continue

        win = r.get("win", False)

        for m in MODULES:

            v = r.get(m)

            if isinstance(v, (int,float)) and v > 0:
                stats[m]["total"] += 1
                if win:
                    stats[m]["wins"] += 1

            elif v is True:
                stats[m]["total"] += 1
                if win:
                    stats[m]["wins"] += 1

    for m in MODULES:

        t = stats[m]["total"]
        w = stats[m]["wins"]

        stats[m]["win_rate"] = (w / t) if t else 0

    return {"module_performance":stats}

def main():

    rows = load_rows()

    intel = compute(rows)

    OUT.write_text(json.dumps(intel,indent=2))

    print("Resolution Intelligence updated")

if __name__ == "__main__":
    main()
