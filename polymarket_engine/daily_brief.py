import json
from pathlib import Path

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")

def main():
    if not LEADERBOARD_PATH.exists():
        print("leaderboard file not found")
        return

    data = json.loads(LEADERBOARD_PATH.read_text(encoding="utf-8"))
    rows = data.get("leaderboard", [])

    lines = []
    lines.append("SIGNALATLAS DAILY BRIEF")
    lines.append("")
    lines.append(f"Signals ranked: {len(rows)}")
    lines.append("")
    lines.append("Top Opportunities")
    lines.append("")

    for row in rows[:5]:
        lines.append(f"{row['rank']}. {row['market_name']}")
        lines.append(f"   Side: {row['side']}")
        lines.append(f"   Edge: {row['total_edge']*100:.2f}%")
        lines.append(f"   Net Edge: {row['expected_net_edge_pct']:.2f}%")
        lines.append(f"   Vacuum: {row['vacuum_score']:.2f}")
        lines.append(f"   Micro: {row['microstructure_score']:.2f}")
        lines.append("")

    text = "\n".join(lines)
    print(text)

    Path("analytics/daily_brief.txt").write_text(text, encoding="utf-8")
    print("file created: analytics/daily_brief.txt")

if __name__ == "__main__":
    main()
