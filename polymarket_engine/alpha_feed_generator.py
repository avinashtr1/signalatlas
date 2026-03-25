import json
from pathlib import Path
from datetime import datetime, timezone

RADAR_PATH = Path("analytics/opportunity_radar.json")
QUALITY_PATH = Path("analytics/alpha_quality_scores.json")
VACUUM_PATH = Path("analytics/liquidity_vacuum_v2.json")
MICRO_PATH = Path("analytics/microstructure_intelligence.json")
STALE_PATH = Path("analytics/stale_repricing.json")

OUT_JSON = Path("analytics/alpha_feed.json")
OUT_TXT = Path("analytics/alpha_feed.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    radar = load_json(RADAR_PATH).get("radar", {})
    quality = load_json(QUALITY_PATH).get("scores", [])
    vacuum = load_json(VACUUM_PATH).get("vacuum_opportunities", [])
    micro = load_json(MICRO_PATH).get("microstructure_signals", [])
    stale = load_json(STALE_PATH).get("stale_repricing_opportunities", [])

    deploy_now = radar.get("deploy_now", [])[:3]
    top_quality = quality[:3]
    top_vacuum = vacuum[:3]
    top_micro = micro[:3]
    top_stale = stale[:3]

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "deploy_now": deploy_now,
        "top_quality": top_quality,
        "top_vacuum": top_vacuum,
        "top_microstructure": top_micro,
        "top_stale_repricing": top_stale,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS ALPHA FEED")
    lines.append("")

    if deploy_now:
        lines.append("DEPLOY NOW")
        for i, r in enumerate(deploy_now, start=1):
            lines.append(
                f"{i}. {r.get('market_name')} | "
                f"side={r.get('side')} | "
                f"edge={float(r.get('total_edge', 0))*100:.2f}% | "
                f"net={float(r.get('expected_net_edge_pct', 0)):.2f}%"
            )
        lines.append("")

    if top_quality:
        lines.append("TOP QUALITY")
        for i, r in enumerate(top_quality, start=1):
            lines.append(
                f"{i}. {r.get('market_name')} | "
                f"grade={r.get('grade')} | "
                f"score={float(r.get('quality_score', 0)):.3f}"
            )
        lines.append("")

    if top_vacuum:
        lines.append("VACUUM")
        for i, r in enumerate(top_vacuum, start=1):
            lines.append(
                f"{i}. {r.get('market_name')} | "
                f"rank={float(r.get('vacuum_rank', 0)):.3f} | "
                f"edge={float(r.get('latest_edge', 0))*100:.2f}%"
            )
        lines.append("")

    if top_micro:
        lines.append("MICROSTRUCTURE")
        for i, r in enumerate(top_micro, start=1):
            lines.append(
                f"{i}. {r.get('market_name')} | "
                f"rank={float(r.get('micro_rank', 0)):.3f} | "
                f"edge={float(r.get('edge', 0))*100:.2f}%"
            )
        lines.append("")

    if top_stale:
        lines.append("STALE REPRICING")
        for i, r in enumerate(top_stale, start=1):
            lines.append(
                f"{i}. {r.get('market_name')} | "
                f"score={float(r.get('stale_repricing_score', 0)):.3f} | "
                f"edge={float(r.get('edge', 0))*100:.2f}% | "
                f"net={float(r.get('net_edge_pct', 0)):.2f}%"
            )
        lines.append("")

    text = "\n".join(lines).strip()
    OUT_TXT.write_text(text, encoding="utf-8")

    print(text)
    print("")
    print("files created:")
    print("analytics/alpha_feed.json")
    print("analytics/alpha_feed.txt")

if __name__ == "__main__":
    main()
