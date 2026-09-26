import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

DETECTED_PATH = Path("logs/signals_detected.jsonl")
OUT_JSON = Path("analytics/liquidity_collapse_report.json")
OUT_TXT = Path("analytics/liquidity_collapse_report.txt")

MIN_SAMPLES = 2
MIN_VACUUM = 0.15
MIN_ABS_MOVE = 0.01   # 1 percentage point
LOW_MICRO_MAX = 0.06

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

def detect(rows):
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
        if len(entries) < MIN_SAMPLES:
            continue

        entries.sort(key=lambda x: x["timestamp"] or "")
        first = entries[0]
        last = entries[-1]

        move = last["entry_price"] - first["entry_price"]
        abs_move = abs(move)
        latest_vacuum = last["vacuum"]
        latest_micro = last["micro"]

        collapse_score = 0.0

        if latest_vacuum >= MIN_VACUUM:
            collapse_score += 0.45
        else:
            collapse_score += max(0.0, latest_vacuum / MIN_VACUUM) * 0.45

        if abs_move >= MIN_ABS_MOVE:
            collapse_score += min(abs_move / 0.03, 1.0) * 0.35

        if latest_micro <= LOW_MICRO_MAX:
            collapse_score += max(0.0, (LOW_MICRO_MAX - latest_micro) / LOW_MICRO_MAX) * 0.20

        collapse_score = round(collapse_score, 6)

        if collapse_score < 0.50:
            continue

        if move > 0:
            direction = "UPWARD_STRESS"
        elif move < 0:
            direction = "DOWNWARD_STRESS"
        else:
            direction = "STATIC_STRESS"

        results.append({
            "market_name": market,
            "bucket": last.get("bucket"),
            "samples": len(entries),
            "first_timestamp": first["timestamp"],
            "last_timestamp": last["timestamp"],
            "first_price": round(first["entry_price"], 6),
            "last_price": round(last["entry_price"], 6),
            "move": round(move, 6),
            "abs_move": round(abs_move, 6),
            "latest_edge": round(last["edge"], 6),
            "latest_net_edge_pct": round(last["net"], 6),
            "latest_vacuum": round(latest_vacuum, 6),
            "latest_micro": round(latest_micro, 6),
            "fill_probability": round(last["fill_probability"], 6),
            "collapse_score": collapse_score,
            "direction": direction,
            "side": last.get("side"),
        })

    results.sort(key=lambda x: x["collapse_score"], reverse=True)
    return results

def to_text(results):
    lines = []
    lines.append("SIGNALATLAS LIQUIDITY COLLAPSE REPORT")
    lines.append("")

    if not results:
        lines.append("No liquidity collapse detected.")
        return "\n".join(lines)

    for i, r in enumerate(results[:10], start=1):
        lines.append(
            f"{i}. {r['market_name']} | "
            f"collapse={r['collapse_score']:.3f} | "
            f"dir={r['direction']} | "
            f"move={r['move']*100:.2f}% | "
            f"vacuum={r['latest_vacuum']:.2f} | "
            f"micro={r['latest_micro']:.2f} | "
            f"edge={r['latest_edge']*100:.2f}%"
        )

    return "\n".join(lines)

def main():
    rows = load_jsonl(DETECTED_PATH)
    results = detect(rows)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "collapses": results,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(to_text(results), encoding="utf-8")

    print(to_text(results))
    print("")
    print("files created:")
    print("analytics/liquidity_collapse_report.json")
    print("analytics/liquidity_collapse_report.txt")

if __name__ == "__main__":
    main()
