import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
RESOLUTION_PATH = Path("analytics/resolution_risk_report.json")
OUT_JSON = Path("analytics/alpha_quality_scores.json")
OUT_TXT = Path("analytics/alpha_quality_scores.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def make_lookup(rows, key):
    out = {}
    for r in rows:
        k = r.get(key)
        if k:
            out[k] = r
    return out

def grade_from_score(score):
    if score >= 0.85:
        return "A+"
    if score >= 0.75:
        return "A"
    if score >= 0.60:
        return "B"
    if score >= 0.45:
        return "C"
    return "D"

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def main():
    lb = load_json(LEADERBOARD_PATH).get("leaderboard", [])
    res = load_json(RESOLUTION_PATH).get("markets", [])
    res_by_market = make_lookup(res, "market_name")

    scored = []

    for row in lb:
        market = row.get("market_name")
        res_row = res_by_market.get(market, {})

        edge = float(row.get("total_edge", 0.0) or 0.0)
        net = float(row.get("expected_net_edge_pct", 0.0) or 0.0)
        vacuum = float(row.get("vacuum_score", 0.0) or 0.0)
        micro = float(row.get("microstructure_score", 0.0) or 0.0)
        fill = float(row.get("expected_fill_probability", 1.0) or 1.0)
        eff = float(res_row.get("capital_efficiency", 0.0) or 0.0)

        # Normalize components
        edge_n = clamp(edge / 0.15)          # 15% total edge ~= max
        net_n = clamp(net / 15.0)            # 15% net edge ~= max
        vac_n = clamp(vacuum / 0.25)         # 0.25 vacuum ~= max
        micro_n = clamp(micro / 0.10)        # 0.10 micro ~= max
        fill_n = clamp(fill)
        eff_n = clamp(eff / 0.30)            # 0.30 efficiency ~= strong

        # Weighted institutional-style alpha score
        quality_score = (
            0.28 * edge_n +
            0.22 * net_n +
            0.12 * vac_n +
            0.08 * micro_n +
            0.10 * fill_n +
            0.20 * eff_n
        )

        quality_score = round(quality_score, 6)
        grade = grade_from_score(quality_score)

        scored.append({
            "market_name": market,
            "bucket_group_title": row.get("bucket_group_title"),
            "side": row.get("side"),
            "total_edge": round(edge, 6),
            "expected_net_edge_pct": round(net, 6),
            "vacuum_score": round(vacuum, 6),
            "microstructure_score": round(micro, 6),
            "expected_fill_probability": round(fill, 6),
            "capital_efficiency": round(eff, 6),
            "quality_score": quality_score,
            "grade": grade,
        })

    scored.sort(key=lambda x: x["quality_score"], reverse=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(scored),
        "scores": scored,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS ALPHA QUALITY SCORES")
    lines.append("")
    if not scored:
        lines.append("No signals scored.")
    else:
        for i, r in enumerate(scored[:10], start=1):
            lines.append(
                f"{i}. {r['market_name']} | "
                f"grade={r['grade']} | "
                f"score={r['quality_score']:.4f} | "
                f"edge={r['total_edge']*100:.2f}% | "
                f"net={r['expected_net_edge_pct']:.2f}% | "
                f"eff={r['capital_efficiency']:.4f}"
            )

    text = "\n".join(lines)
    OUT_TXT.write_text(text, encoding="utf-8")

    print(text)
    print("")
    print("files created:")
    print("analytics/alpha_quality_scores.json")
    print("analytics/alpha_quality_scores.txt")

if __name__ == "__main__":
    main()
