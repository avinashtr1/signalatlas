import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

SNAP = Path("analytics/market_snapshots.json")
OUT = Path("analytics/liquidity_vacuum_v2.json")

MIN_ROWS = 2
BID_DROP_THRESHOLD = 0.50
ASK_DROP_THRESHOLD = 0.50
SPREAD_WIDEN_THRESHOLD = 1.50
IMBALANCE_FLIP_THRESHOLD = 0.40

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

def main():
    snap = load_json(SNAP)
    rows = snap.get("rows", [])

    by_market = defaultdict(list)
    for r in rows:
        name = r.get("market_name")
        if name:
            by_market[name].append(r)

    signals = []

    for name, items in by_market.items():
        items = sorted(items, key=lambda x: x.get("timestamp", ""))
        if len(items) < MIN_ROWS:
            continue

        prev = items[-2]
        curr = items[-1]

        prev_bid = to_float(prev.get("bid_depth"), None)
        curr_bid = to_float(curr.get("bid_depth"), None)
        prev_ask = to_float(prev.get("ask_depth"), None)
        curr_ask = to_float(curr.get("ask_depth"), None)
        prev_spread = to_float(prev.get("spread"), None)
        curr_spread = to_float(curr.get("spread"), None)
        prev_imb = to_float(prev.get("orderbook_imbalance"), None)
        curr_imb = to_float(curr.get("orderbook_imbalance"), None)

        bid_drop = None
        ask_drop = None
        spread_ratio = None
        imbalance_flip = False

        if prev_bid is not None and curr_bid is not None and prev_bid > 0:
            bid_drop = (prev_bid - curr_bid) / prev_bid

        if prev_ask is not None and curr_ask is not None and prev_ask > 0:
            ask_drop = (prev_ask - curr_ask) / prev_ask

        if prev_spread is not None and curr_spread is not None and prev_spread > 0:
            spread_ratio = curr_spread / prev_spread

        if prev_imb is not None and curr_imb is not None:
            if abs(curr_imb - prev_imb) >= IMBALANCE_FLIP_THRESHOLD:
                imbalance_flip = True

        vacuum_score = 0.0
        state_parts = []

        if bid_drop is not None and bid_drop >= BID_DROP_THRESHOLD:
            vacuum_score += 0.35
            state_parts.append("bid_vacuum")

        if ask_drop is not None and ask_drop >= ASK_DROP_THRESHOLD:
            vacuum_score += 0.35
            state_parts.append("ask_vacuum")

        if spread_ratio is not None and spread_ratio >= SPREAD_WIDEN_THRESHOLD:
            vacuum_score += 0.20
            state_parts.append("spread_widen")

        if imbalance_flip:
            vacuum_score += 0.10
            state_parts.append("imbalance_flip")

        if vacuum_score >= 0.45:
            signals.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_name": name,
                "vacuum_score": round(vacuum_score, 6),
                "bid_drop": None if bid_drop is None else round(bid_drop, 6),
                "ask_drop": None if ask_drop is None else round(ask_drop, 6),
                "spread_ratio": None if spread_ratio is None else round(spread_ratio, 6),
                "prev_imbalance": prev_imb,
                "curr_imbalance": curr_imb,
                "state": ",".join(state_parts)
            })

    signals.sort(key=lambda x: x["vacuum_score"], reverse=True)

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "signals": signals
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("LIQUIDITY VACUUM V2 ENGINE BUILT")
    print("signals:", len(signals))
    print("file:", OUT)

if __name__ == "__main__":
    main()
