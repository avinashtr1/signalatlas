import json
from pathlib import Path

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
RADAR_PATH = Path("analytics/opportunity_radar.json")
OUT_PATH = Path("analytics/public_feed.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    leaderboard = load_json(LEADERBOARD_PATH).get("leaderboard", [])
    radar = load_json(RADAR_PATH).get("radar", {})

    lines = []
    lines.append("SIGNALATLAS LABS")
    lines.append("Event Intelligence")
    lines.append("")

    deploy = radar.get("deploy_now", [])
    if deploy:
        top = deploy[0]
    elif leaderboard:
        top = leaderboard[0]
    else:
        top = None

    if top:
        lines.append("TOP OPPORTUNITY")
        lines.append(f"Market: {top['market_name']}")
        lines.append(f"Side: {top['side']}")
        lines.append(f"Edge: {float(top.get('total_edge', 0))*100:.2f}%")
        lines.append(f"Net Edge: {float(top.get('expected_net_edge_pct', 0)):.2f}%")
        lines.append(f"Vacuum: {float(top.get('vacuum_score', 0)):.2f}")
        lines.append(f"Micro: {float(top.get('microstructure_score', 0)):.2f}")
        lines.append("")

    lines.append("TODAY'S INTELLIGENCE")
    if not leaderboard:
        lines.append("No qualifying opportunities.")
    else:
        for i, row in enumerate(leaderboard[:3], start=1):
            lines.append(
                f"{i}. {row['market_name']} | "
                f"edge={float(row.get('total_edge', 0))*100:.2f}% | "
                f"net={float(row.get('expected_net_edge_pct', 0)):.2f}%"
            )

    text = "\n".join(lines)
    OUT_PATH.write_text(text, encoding="utf-8")

    print(text)
    print("")
    print("file created: analytics/public_feed.txt")

if __name__ == "__main__":
    main()
