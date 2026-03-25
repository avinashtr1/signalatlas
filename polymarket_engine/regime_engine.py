import json
from pathlib import Path
from datetime import datetime, timezone

RADAR = Path("analytics/radar_live.json")
OPP = Path("analytics/opportunity_scores.json")
OUT = Path("analytics/market_regime.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def main():
    radar = load_json(RADAR)
    opp = load_json(OPP)

    markets = radar.get("markets", [])
    opps = opp.get("markets", [])

    stale = 0
    momentum_up = 0
    high_scores = 0

    for m in markets:
        if m.get("freshness") == "stale":
            stale += 1
        if m.get("momentum_state") == "up":
            momentum_up += 1

    for o in opps:
        if o.get("opportunity_score",0) > 0.5:
            high_scores += 1

    regime = "calm"

    if momentum_up > 2:
        regime = "trending"

    if stale > len(markets) * 0.7:
        regime = "liquidity_lag"

    if high_scores > 2:
        regime = "volatile"

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets_scanned": len(markets),
        "momentum_up": momentum_up,
        "stale_markets": stale,
        "high_score_markets": high_scores,
        "regime": regime
    }

    OUT.write_text(json.dumps(out, indent=2))

    print("REGIME ENGINE BUILT")
    print("regime:", regime)

if __name__ == "__main__":
    main()
