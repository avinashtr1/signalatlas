import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD = Path("analytics/alpha_leaderboard.json")
QUALITY = Path("analytics/alpha_quality_scores.json")

OUT_JSON = Path("analytics/microstructure_intelligence.json")
OUT_TXT = Path("analytics/microstructure_intelligence.txt")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def build_quality_map():
    data = load_json(QUALITY)
    out = {}
    for r in data.get("scores", []):
        name = r.get("market_name")
        if name:
            out[name] = r
    return out

def detect():
    leaderboard = load_json(LEADERBOARD).get("leaderboard", [])
    quality_map = build_quality_map()

    signals = []

    for r in leaderboard:

        name = r.get("market_name")

        edge = float(r.get("total_edge", 0.0) or 0.0)
        vacuum = float(r.get("vacuum_score", 0.0) or 0.0)
        micro = float(r.get("microstructure_score", 0.0) or 0.0)
        fill = float(r.get("expected_fill_probability", 1.0) or 1.0)

        q = quality_map.get(name, {})
        quality = float(q.get("quality_score", 0.0) or 0.0)

        spread_pressure = clamp(micro / 0.10)
        vacuum_pressure = clamp(vacuum / 0.25)
        edge_component = clamp(edge / 0.15)
        quality_component = clamp(quality)

        micro_rank = round(
            0.35 * vacuum_pressure +
            0.25 * spread_pressure +
            0.20 * edge_component +
            0.20 * quality_component,
            6
        )

        if micro_rank < 0.40:
            continue

        signals.append({
            "market_name": name,
            "bucket": r.get("bucket_group_title"),
            "side": r.get("side"),
            "edge": edge,
            "vacuum": vacuum,
            "microstructure": micro,
            "fill_probability": fill,
            "quality_score": quality,
            "micro_rank": micro_rank
        })

    signals.sort(key=lambda x: x["micro_rank"], reverse=True)

    return signals

def to_text(signals):

    lines = []
    lines.append("SIGNALATLAS MICROSTRUCTURE INTELLIGENCE")
    lines.append("")

    if not signals:
        lines.append("No microstructure signals detected.")
        return "\n".join(lines)

    for i, r in enumerate(signals[:10], start=1):

        lines.append(
            f"{i}. {r['market_name']} | "
            f"rank={r['micro_rank']:.3f} | "
            f"vacuum={r['vacuum']:.2f} | "
            f"micro={r['microstructure']:.2f} | "
            f"edge={r['edge']*100:.2f}%"
        )

    return "\n".join(lines)

def main():

    signals = detect()

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "microstructure_signals": signals
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(to_text(signals), encoding="utf-8")

    print(to_text(signals))
    print("")
    print("files created:")
    print("analytics/microstructure_intelligence.json")
    print("analytics/microstructure_intelligence.txt")

if __name__ == "__main__":
    main()
