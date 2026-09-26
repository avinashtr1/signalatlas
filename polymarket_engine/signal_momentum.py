import json
from pathlib import Path
from datetime import datetime, timezone

MEM = Path("analytics/signal_memory.jsonl")
OUT = Path("analytics/signal_momentum.json")

FIELDS = [
    "vacuum_score",
    "microstructure_score",
    "stale_repricing_score",
    "resolution_arb_v2_score",
    "collapse_v2_score",
    "shock_score",
]

def load_rows():
    rows = []
    if not MEM.exists():
        return rows
    with MEM.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows

def group_last_n(rows, n=4):
    grouped = {}
    for r in rows:
        name = r.get("market_name")
        if not name:
            continue
        grouped.setdefault(name, []).append(r)
    out = {}
    for name, arr in grouped.items():
        out[name] = arr[-n:]
    return out

def composite(r):
    vals = [float(r.get(f, 0) or 0) for f in FIELDS]
    return sum(vals)

def classify(delta):
    if delta >= 0.25:
        return "accelerating"
    if delta >= 0.08:
        return "rising"
    if delta <= -0.25:
        return "breaking_down"
    if delta <= -0.08:
        return "fading"
    return "flat"

def main():
    rows = load_rows()
    grouped = group_last_n(rows, n=4)

    markets = []
    for name, arr in grouped.items():
        comps = [round(composite(x), 6) for x in arr]
        if len(comps) >= 2:
            delta = round(comps[-1] - comps[0], 6)
        else:
            delta = 0.0

        markets.append({
            "market_name": name,
            "samples": len(comps),
            "composite_series": comps,
            "momentum_delta": delta,
            "momentum_state": classify(delta),
        })

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets": markets,
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("SIGNAL MOMENTUM BUILT")
    print("markets:", len(markets))
    print("file: analytics/signal_momentum.json")

if __name__ == "__main__":
    main()
