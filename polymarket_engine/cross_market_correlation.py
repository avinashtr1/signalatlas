import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD = Path("analytics/alpha_leaderboard.json")
OUT = Path("analytics/cross_market_correlation.json")

KEYWORDS = {
    "election_us_2028": ["president", "white house", "election"],
    "senate_control": ["senate", "upper chamber"],
    "house_control": ["house", "lower chamber"],
    "nba_finals": ["nba", "finals", "conference finals"],
    "crypto_btc": ["bitcoin", "btc"],
    "crypto_eth": ["ethereum", "eth"],
}

def load_rows():
    if not LEADERBOARD.exists():
        return []
    data = json.loads(LEADERBOARD.read_text(encoding="utf-8"))
    return data.get("leaderboard", [])

def group_name(name: str) -> str:
    n = (name or "").lower()
    for group, kws in KEYWORDS.items():
        if any(k in n for k in kws):
            return group
    return "other"

def avg(xs):
    return sum(xs) / len(xs) if xs else 0.0

def main():
    rows = load_rows()

    buckets = {}
    for r in rows:
        g = group_name(r.get("market_name", ""))
        buckets.setdefault(g, []).append(r)

    groups = []
    divergences = []

    for g, arr in buckets.items():
        edges = [float(x.get("expected_net_edge_pct", 0) or 0) for x in arr]
        radars = [float(x.get("adaptive_radar_score", 0) or 0) for x in arr]
        vacs = [float(x.get("vacuum_score", 0) or 0) for x in arr]
        stales = [float(x.get("stale_repricing_score", 0) or 0) for x in arr]

        edge_avg = avg(edges)
        radar_avg = avg(radars)
        vac_avg = avg(vacs)
        stale_avg = avg(stales)

        groups.append({
            "cluster": g,
            "markets": len(arr),
            "avg_net_edge_pct": round(edge_avg, 4),
            "avg_radar_score": round(radar_avg, 6),
            "avg_vacuum_score": round(vac_avg, 4),
            "avg_stale_score": round(stale_avg, 4),
        })

        for r in arr:
            edge = float(r.get("expected_net_edge_pct", 0) or 0)
            radar = float(r.get("adaptive_radar_score", 0) or 0)
            div = abs(edge - edge_avg) + abs(radar - radar_avg)

            if div >= 3.0:
                divergences.append({
                    "cluster": g,
                    "market_name": r.get("market_name"),
                    "expected_net_edge_pct": round(edge, 4),
                    "adaptive_radar_score": round(radar, 6),
                    "cluster_avg_net_edge_pct": round(edge_avg, 4),
                    "cluster_avg_radar_score": round(radar_avg, 6),
                    "divergence_score": round(div, 4),
                })

    divergences.sort(key=lambda x: x["divergence_score"], reverse=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "clusters": groups,
        "divergences": divergences[:20],
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("CROSS MARKET CORRELATION BUILT")
    print("clusters:", len(groups))
    print("divergences:", len(payload["divergences"]))
    print("file: analytics/cross_market_correlation.json")

if __name__ == "__main__":
    main()
