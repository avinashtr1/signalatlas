import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

SNAP = Path("analytics/market_snapshots.json")
OUT = Path("analytics/resolution_arbitrage_signals.json")

MIN_EDGE = 0.05  # 5% mismatch threshold


def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def normalize_name(name: str) -> str:
    return (name or "").strip().lower()


def cluster_key(name: str) -> str:
    n = normalize_name(name)

    if "senate" in n and "2026" in n:
        return "us_senate_2026"
    if "western conference finals" in n:
        return "nba_west_conf"
    if "eastern conference finals" in n:
        return "nba_east_conf"

    # fallback: first 6 words
    parts = n.split()
    return "_".join(parts[:6]) if parts else "unknown"


def side_hint(name: str) -> str:
    n = normalize_name(name)

    if "democratic" in n or "democrats" in n:
        return "DEM"
    if "republican" in n or "republicans" in n:
        return "REP"
    if "will " in n and "?" in n:
        return "YES_EVENT"

    return "UNK"


def main():
    snap = load_json(SNAP)
    rows = snap.get("rows", [])

    latest_by_market = {}
    for r in rows:
        name = r.get("market_name")
        if name:
            latest_by_market[name] = r

    clusters = defaultdict(list)
    for name, r in latest_by_market.items():
        k = cluster_key(name)
        clusters[k].append({
            "market_name": name,
            "market_probability": float(r.get("radar_score", 0.0) or 0.0),
            "opportunity_score": float(r.get("opportunity_score", 0.0) or 0.0),
            "side_hint": side_hint(name),
        })

    signals = []

    for k, items in clusters.items():
        if len(items) < 2:
            continue

        total_prob = sum(x["market_probability"] for x in items)
        arb_edge = abs(1.0 - total_prob)

        if arb_edge >= MIN_EDGE:
            signals.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cluster": k,
                "market_count": len(items),
                "sum_probability": round(total_prob, 4),
                "arb_edge": round(arb_edge, 4),
                "markets": items,
            })

    signals.sort(key=lambda x: x["arb_edge"], reverse=True)

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "signals": signals,
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("RESOLUTION ARBITRAGE ENGINE BUILT")
    print("signals:", len(signals))
    print("file:", OUT)


if __name__ == "__main__":
    main()
