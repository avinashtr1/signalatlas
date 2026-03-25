import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
OUT_JSON = Path("analytics/resolution_risk_report.json")
OUT_TXT = Path("analytics/resolution_risk_report.txt")

# placeholder assumption if resolution ETA not known yet
DEFAULT_DAYS = 180


def load_rows():
    if not LEADERBOARD_PATH.exists():
        return []
    data = json.loads(LEADERBOARD_PATH.read_text())
    return data.get("leaderboard", [])


def estimate_resolution_days(row):
    """
    Placeholder until we pull real resolution timestamps
    from the adapter.
    """
    return DEFAULT_DAYS


def compute_metrics(rows):

    results = []

    for r in rows:

        edge = float(r.get("total_edge", 0.0) or 0.0)
        days = estimate_resolution_days(r)

        if days <= 0:
            continue

        annualized_edge = edge * (365 / days)

        efficiency = annualized_edge * float(
            r.get("expected_fill_probability", 1.0) or 1.0
        )

        results.append({
            "market_name": r.get("market_name"),
            "bucket": r.get("bucket_group_title"),
            "edge": edge,
            "resolution_days": days,
            "annualized_edge": round(annualized_edge, 6),
            "capital_efficiency": round(efficiency, 6),
        })

    results.sort(key=lambda x: x["capital_efficiency"], reverse=True)

    return results


def to_text(rows):

    lines = []
    lines.append("SIGNALATLAS RESOLUTION RISK MODEL")
    lines.append("")

    if not rows:
        lines.append("No markets available.")
        return "\n".join(lines)

    for i, r in enumerate(rows[:10], start=1):
        lines.append(
            f"{i}. {r['market_name']} | "
            f"edge={r['edge']:.4f} | "
            f"days={r['resolution_days']} | "
            f"annualized={r['annualized_edge']:.4f} | "
            f"efficiency={r['capital_efficiency']:.4f}"
        )

    return "\n".join(lines)


def main():

    rows = load_rows()
    results = compute_metrics(rows)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets": results,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2))
    OUT_TXT.write_text(to_text(results))

    print(to_text(results))
    print("")
    print("files created:")
    print("analytics/resolution_risk_report.json")
    print("analytics/resolution_risk_report.txt")


if __name__ == "__main__":
    main()
