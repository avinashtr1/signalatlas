import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

DETECTED_PATH = Path("logs/signals_detected.jsonl")
QUALITY_PATH = Path("analytics/alpha_quality_scores.json")
OUT_JSON = Path("analytics/liquidity_vacuum_v2.json")
OUT_TXT = Path("analytics/liquidity_vacuum_v2.txt")

MIN_SAMPLES = 2

def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def load_quality_map():
    if not QUALITY_PATH.exists():
        return {}
    data = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))
    out = {}
    for r in data.get("scores", []):
        name = r.get("market_name")
        if name:
            out[name] = r
    return out

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def detect(rows, quality_map):
    by_market = defaultdict(list)

    for r in rows:
        market = r.get("market_name") or "UNKNOWN"
        by_market[market].append({
            "timestamp": r.get("timestamp"),
            "entry_price": float(r.get("entry_price", 0.0) or 0.0),
            "edge": float(r.get("edge", 0.0) or 0.0),
            "net": float(r.get("expected_net_edge_pct", 0.0) or 0.0),
            "vacuum": float(r.get("vacuum_score", 0.0) or 0.0),
            "micro": float(r.get("microstructure_score", 0.0) or 0.0),
            "fill_probability": float(r.get("fill_probability", 1.0) or 1.0),
            "side": r.get("side"),
            "bucket": r.get("bucket"),
        })

    results = []

    for market, entries in by_market.items():
        entries.sort(key=lambda x: x["timestamp"] or "")
        last = entries[-1]
        first = entries[0]

        move = abs(last["entry_price"] - first["entry_price"]) if len(entries) >= MIN_SAMPLES else 0.0
        q = quality_map.get(market, {})
        quality_score = float(q.get("quality_score", 0.0) or 0.0)

        vacuum_component = clamp(last["vacuum"] / 0.25)
        move_component = clamp(move / 0.03)
        fill_component = clamp(last["fill_probability"])
        edge_component = clamp(last["edge"] / 0.15)
        quality_component = clamp(quality_score)

        vacuum_rank = round(
            0.35 * vacuum_component +
            0.20 * move_component +
            0.15 * fill_component +
            0.15 * edge_component +
            0.15 * quality_component,
            6
        )

        if vacuum_rank < 0.35:
            continue

        results.append({
            "market_name": market,
            "bucket": last.get("bucket"),
            "side": last.get("side"),
            "samples": len(entries),
            "latest_vacuum_score": round(last["vacuum"], 6),
            "latest_micro_score": round(last["micro"], 6),
            "latest_edge": round(last["edge"], 6),
            "latest_net_edge_pct": round(last["net"], 6),
            "latest_fill_probability": round(last["fill_probability"], 6),
            "price_move_abs": round(move, 6),
            "quality_score": round(quality_score, 6),
            "vacuum_rank": vacuum_rank,
        })

    results.sort(key=lambda x: x["vacuum_rank"], reverse=True)
    return results

def to_text(results):
    lines = []
    lines.append("SIGNALATLAS LIQUIDITY VACUUM V2")
    lines.append("")

    if not results:
        lines.append("No vacuum opportunities detected.")
        return "\n".join(lines)

    for i, r in enumerate(results[:10], start=1):
        lines.append(
            f"{i}. {r['market_name']} | "
            f"rank={r['vacuum_rank']:.3f} | "
            f"vacuum={r['latest_vacuum_score']:.2f} | "
            f"edge={r['latest_edge']*100:.2f}% | "
            f"net={r['latest_net_edge_pct']:.2f}% | "
            f"fill={r['latest_fill_probability']:.2f} | "
            f"quality={r['quality_score']:.3f}"
        )

    return "\n".join(lines)

def main():
    rows = load_jsonl(DETECTED_PATH)
    quality_map = load_quality_map()
    results = detect(rows, quality_map)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "vacuum_opportunities": results,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(to_text(results), encoding="utf-8")

    print(to_text(results))
    print("")
    print("files created:")
    print("analytics/liquidity_vacuum_v2.json")
    print("analytics/liquidity_vacuum_v2.txt")

if __name__ == "__main__":
    main()
