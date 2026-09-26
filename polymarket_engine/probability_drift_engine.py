import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

DETECTED_PATH = Path("logs/signals_detected.jsonl")
OUT_JSON = Path("analytics/probability_drift_report.json")
OUT_TXT = Path("analytics/probability_drift_report.txt")

MIN_SAMPLES = 2
MIN_ABS_MOVE = 0.01   # 1 percentage point
STRONG_MOVE = 0.03    # 3 percentage points

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

def classify_drift(move):
    abs_move = abs(move)
    if abs_move >= STRONG_MOVE:
        return "STRONG"
    if abs_move >= MIN_ABS_MOVE:
        return "MODERATE"
    return "NONE"

def detect_drift(rows):
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
        drift_class = classify_drift(move)

        if drift_class == "NONE":
            continue

        # crude interpretation layer for now
        if move > 0:
            interpretation = "UPWARD_PROBABILITY_DRIFT"
        else:
            interpretation = "DOWNWARD_PROBABILITY_DRIFT"

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
            "drift_class": drift_class,
            "interpretation": interpretation,
            "latest_edge": round(last["edge"], 6),
            "latest_net_edge_pct": round(last["net"], 6),
            "latest_vacuum": round(last["vacuum"], 6),
            "latest_micro": round(last["micro"], 6),
            "side": last.get("side"),
        })

    results.sort(key=lambda x: x["abs_move"], reverse=True)
    return results

def to_text(results):
    lines = []
    lines.append("SIGNALATLAS PROBABILITY DRIFT REPORT")
    lines.append("")

    if not results:
        lines.append("No significant probability drift detected.")
        return "\n".join(lines)

    for i, r in enumerate(results[:10], start=1):
        lines.append(
            f"{i}. {r['market_name']} | "
            f"move={r['move']*100:.2f}% | "
            f"class={r['drift_class']} | "
            f"edge={r['latest_edge']*100:.2f}% | "
            f"net={r['latest_net_edge_pct']:.2f}% | "
            f"vacuum={r['latest_vacuum']:.2f} | "
            f"micro={r['latest_micro']:.2f}"
        )

    return "\n".join(lines)

def main():
    rows = load_jsonl(DETECTED_PATH)
    results = detect_drift(rows)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "drift_markets": results,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(to_text(results), encoding="utf-8")

    print(to_text(results))
    print("")
    print("files created:")
    print("analytics/probability_drift_report.json")
    print("analytics/probability_drift_report.txt")

if __name__ == "__main__":
    main()
