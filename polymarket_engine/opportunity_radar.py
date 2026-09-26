import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
OUT_PATH = Path("analytics/opportunity_radar.json")
TXT_PATH = Path("analytics/opportunity_radar.txt")

def load_leaderboard():
    if not LEADERBOARD_PATH.exists():
        return []
    data = json.loads(LEADERBOARD_PATH.read_text(encoding="utf-8"))
    return data.get("leaderboard", [])

def classify(rows):
    deploy_now = []
    watchlist = []
    vacuum = []
    near_resolution = []

    for r in rows:
        edge = float(r.get("total_edge", 0.0) or 0.0)
        net = float(r.get("expected_net_edge_pct", 0.0) or 0.0)
        vac = float(r.get("vacuum_score", 0.0) or 0.0)
        micro = float(r.get("microstructure_score", 0.0) or 0.0)

        # DEPLOY NOW = strongest clean opportunities
        if edge >= 0.12 and net >= 10.0:
            deploy_now.append(r)

        # WATCHLIST = decent edge, not top-tier
        elif edge >= 0.08:
            watchlist.append(r)

        # standalone vacuum classification
        if vac >= 0.15:
            vacuum.append(r)

        # placeholder for future true resolution logic
        # currently use strong edge + weak vacuum as rough proxy
        if edge >= 0.10 and vac < 0.05 and micro >= 0.05:
            near_resolution.append(r)

    return {
        "deploy_now": deploy_now[:5],
        "watchlist": watchlist[:5],
        "vacuum": vacuum[:5],
        "near_resolution": near_resolution[:5],
    }

def to_text(radar):
    lines = []
    lines.append("SIGNALATLAS OPPORTUNITY RADAR")
    lines.append("")

    sections = [
        ("DEPLOY NOW", radar.get("deploy_now", [])),
        ("WATCHLIST", radar.get("watchlist", [])),
        ("VACUUM", radar.get("vacuum", [])),
        ("NEAR RESOLUTION", radar.get("near_resolution", [])),
    ]

    for title, rows in sections:
        lines.append(title)
        if not rows:
            lines.append("  none")
            lines.append("")
            continue

        for i, r in enumerate(rows, start=1):
            lines.append(
                f"{i}. {r.get('market_name')} | "
                f"edge={float(r.get('total_edge', 0.0))*100:.2f}% | "
                f"net={float(r.get('expected_net_edge_pct', 0.0)):.2f}% | "
                f"vacuum={float(r.get('vacuum_score', 0.0)):.2f} | "
                f"micro={float(r.get('microstructure_score', 0.0)):.2f}"
            )
        lines.append("")

    return "\n".join(lines)

def main():
    rows = load_leaderboard()
    radar = classify(rows)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "radar": radar,
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    text = to_text(radar)
    TXT_PATH.write_text(text, encoding="utf-8")

    print(text)
    print("files created:")
    print("analytics/opportunity_radar.json")
    print("analytics/opportunity_radar.txt")

if __name__ == "__main__":
    main()
