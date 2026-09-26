import json
from pathlib import Path
from datetime import datetime, timezone

MEM = Path("analytics/signal_memory.jsonl")
OUT = Path("analytics/signal_state_change.json")

FIELDS = [
    "vacuum_score",
    "microstructure_score",
    "stale_repricing_score",
    "resolution_arb_v2_score",
    "collapse_v2_score",
    "shock_score"
]

def load_rows():
    rows = []
    if not MEM.exists():
        return rows

    with MEM.open() as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except:
                pass

    return rows

def compute(rows):

    latest = {}
    prev = {}

    for r in rows:
        m = r.get("market_name")
        if not m:
            continue

        if m not in latest:
            latest[m] = r
        else:
            prev[m] = latest[m]
            latest[m] = r

    results = []

    for m in latest:

        r = latest[m]
        p = prev.get(m)

        deltas = {}

        for f in FIELDS:
            now = r.get(f, 0) or 0
            old = 0 if not p else (p.get(f, 0) or 0)
            deltas[f.replace("_score","_delta")] = round(now - old, 4)

        state_score = sum(abs(v) for v in deltas.values())

        freshness = "persistent"
        if state_score > 0.25:
            freshness = "fresh"
        elif state_score > 0.10:
            freshness = "emerging"
        elif state_score < 0.02:
            freshness = "stale"

        results.append({
            "market_name": m,
            "state_change_score": round(state_score,4),
            "freshness": freshness,
            "deltas": deltas
        })

    return results

def main():

    rows = load_rows()

    res = compute(rows)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets": res
    }

    OUT.write_text(json.dumps(payload,indent=2))

    print("STATE CHANGE ENGINE BUILT")
    print("markets analysed:", len(res))
    print("file:", OUT)

if __name__ == "__main__":
    main()
