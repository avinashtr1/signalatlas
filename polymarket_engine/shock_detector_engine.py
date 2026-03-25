import json
from pathlib import Path
from datetime import datetime, timezone

SNAP = Path("analytics/market_snapshots.json")
OUT = Path("analytics/market_shocks.json")

PROB_THRESHOLD = 0.04
LIQ_THRESHOLD = 0.60

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def main():
    snap = load_json(SNAP).get("rows", [])

    shocks = []

    by_market = {}

    for r in snap:
        m = r["market_name"]
        by_market.setdefault(m, []).append(r)

    for m, rows in by_market.items():

        if len(rows) < 2:
            continue

        old = rows[-2]
        new = rows[-1]

        p_old = old.get("radar_score",0)
        p_new = new.get("radar_score",0)

        delta = p_new - p_old

        liq_old = old.get("liquidity",1)
        liq_new = new.get("liquidity",1)

        if liq_old > 0:
            liq_drop = (liq_old - liq_new) / liq_old
        else:
            liq_drop = 0

        if abs(delta) >= PROB_THRESHOLD or liq_drop >= LIQ_THRESHOLD:

            shocks.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_name": m,
                "prob_move": delta,
                "liquidity_drop": liq_drop
            })

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(shocks),
        "shocks": shocks
    }

    OUT.write_text(json.dumps(out,indent=2))

    print("SHOCK ENGINE BUILT")
    print("shocks:",len(shocks))
    print("file:",OUT)

if __name__=="__main__":
    main()
