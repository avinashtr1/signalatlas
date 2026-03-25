import json
from pathlib import Path
from datetime import datetime, timezone

RADAR = Path("analytics/radar_live.json")
OPP = Path("analytics/opportunity_scores.json")
REGIME = Path("analytics/market_regime.json")
OUT = Path("analytics/market_snapshots.json")

MAX_ROWS = 3000
MAX_ACTIVE_MARKETS = 60

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def to_float(x, default=None):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default

def pick(*vals):
    for v in vals:
        if v is not None:
            return v
    return None

def main():
    radar = load_json(RADAR)
    opp = load_json(OPP)
    regime = load_json(REGIME)

    opp_map = {}
    for r in opp.get("markets", []):
        name = r.get("market_name")
        if name:
            opp_map[name] = r

    rows = []
    active_markets = (radar.get("deploy_now", []) + radar.get("watchlist", []))[:MAX_ACTIVE_MARKETS]
    for r in active_markets:
        name = r.get("market_name")
        o = opp_map.get(name, {})

        best_bid = to_float(pick(
            r.get("best_bid"), r.get("bestBid"), r.get("bid"),
            o.get("best_bid"), o.get("bestBid"), o.get("bid")
        ))

        best_ask = to_float(pick(
            r.get("best_ask"), r.get("bestAsk"), r.get("ask"),
            o.get("best_ask"), o.get("bestAsk"), o.get("ask")
        ))

        bid_depth = to_float(pick(
            r.get("bid_depth"), r.get("bidDepth"),
            o.get("bid_depth"), o.get("bidDepth")
        ))

        ask_depth = to_float(pick(
            r.get("ask_depth"), r.get("askDepth"),
            o.get("ask_depth"), o.get("askDepth")
        ))

        volume = to_float(pick(
            r.get("volume"), r.get("volume_1m"), r.get("volume_5m"),
            o.get("volume"), o.get("volume_1m"), o.get("volume_5m")
        ))

        mid_price = None
        if best_bid is not None and best_ask is not None:
            mid_price = (best_bid + best_ask) / 2.0

        spread = None
        if best_bid is not None and best_ask is not None:
            spread = best_ask - best_bid

        orderbook_imbalance = None
        if bid_depth is not None and ask_depth is not None and (bid_depth + ask_depth) > 0:
            orderbook_imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)

        rows.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_name": name,
            "market_environment": regime.get("regime", "unknown"),
            "radar_score": to_float(r.get("adaptive_radar_score"), 0.0),
            "opportunity_score": to_float(o.get("opportunity_score"), 0.0),
            "expected_value": to_float(o.get("expected_value"), 0.0),
            "confidence_score": to_float(o.get("confidence_score"), 0.0),
            "execution_urgency": to_float(o.get("execution_urgency"), 0.0),
            "freshness": r.get("freshness", "unknown"),
            "momentum_state": r.get("momentum_state", "unknown"),

            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid_price": mid_price,
            "spread": spread,
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "orderbook_imbalance": orderbook_imbalance,
            "volume": volume,
        })

    doc = load_json(OUT)
    history = doc.get("rows", [])
    history.extend(rows)
    history = history[-MAX_ROWS:]

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(history),
        "rows": history,
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("MARKET SNAPSHOT ENGINE V2 BUILT")
    print("rows_added:", len(rows))
    print("total_rows:", len(history))
    print("file:", OUT)

if __name__ == "__main__":
    main()
