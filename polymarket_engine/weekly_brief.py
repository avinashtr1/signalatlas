import json
from pathlib import Path

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
RADAR_PATH = Path("analytics/opportunity_radar.json")
SHOCK_PATH = Path("analytics/probability_shocks.json")
REPUTATION_PATH = Path("analytics/reputation_summary.json")
OUT_PATH = Path("analytics/weekly_brief.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    leaderboard = load_json(LEADERBOARD_PATH).get("leaderboard", [])
    radar = load_json(RADAR_PATH).get("radar", {})
    shocks = load_json(SHOCK_PATH).get("shocks", [])
    rep = load_json(REPUTATION_PATH)

    lines = []
    lines.append("SIGNALATLAS WEEKLY INTELLIGENCE")
    lines.append("")
    lines.append(f"Signals Generated: {rep.get('signals_generated', 0)}")
    lines.append(f"Signals Resolved: {rep.get('signals_resolved', 0)}")
    lines.append(f"Win Rate: {float(rep.get('win_rate', 0))*100:.2f}%")
    lines.append(f"Realized PnL: {float(rep.get('realized_pnl', 0)):.4f}")
    lines.append("")

    lines.append("TOP OPPORTUNITIES")
    if not leaderboard:
        lines.append("none")
    else:
        for i, row in enumerate(leaderboard[:5], start=1):
            lines.append(
                f"{i}. {row['market_name']} | "
                f"edge={float(row.get('total_edge', 0))*100:.2f}% | "
                f"net={float(row.get('expected_net_edge_pct', 0)):.2f}%"
            )
    lines.append("")

    lines.append("DEPLOY NOW")
    deploy = radar.get("deploy_now", [])
    if not deploy:
        lines.append("none")
    else:
        for i, row in enumerate(deploy[:5], start=1):
            lines.append(
                f"{i}. {row['market_name']} | edge={float(row.get('total_edge', 0))*100:.2f}%"
            )
    lines.append("")

    lines.append("PROBABILITY SHOCKS")
    if not shocks:
        lines.append("none")
    else:
        for i, s in enumerate(shocks[:5], start=1):
            lines.append(
                f"{i}. {s['market_name']} | move={float(s['move'])*100:.2f}% | samples={s['samples']}"
            )
    lines.append("")

    text = "\n".join(lines)
    OUT_PATH.write_text(text, encoding="utf-8")
    print(text)
    print("")
    print("file created: analytics/weekly_brief.txt")

if __name__ == "__main__":
    main()
