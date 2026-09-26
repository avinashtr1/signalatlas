import json
from pathlib import Path
from datetime import datetime, timezone

MEM = Path("analytics/signal_memory.jsonl")
OUT = Path("analytics/signal_confidence.json")

FIELDS = [
    "vacuum_score",
    "microstructure_score",
    "stale_repricing_score",
    "resolution_arb_v2_score",
    "collapse_v2_score",
    "shock_score",
]

def load_rows():
    rows = []
    if not MEM.exists():
        return rows
    with MEM.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows

def group_rows(rows):
    grouped = {}
    for r in rows:
        name = r.get("market_name")
        if not name:
            continue
        grouped.setdefault(name, []).append(r)
    return grouped

def avg(vals):
    return sum(vals) / len(vals) if vals else 0.0

def variance(vals):
    if len(vals) < 2:
        return 0.0
    m = avg(vals)
    return sum((x - m) ** 2 for x in vals) / len(vals)

def tier(score):
    if score >= 0.80:
        return "A"
    if score >= 0.65:
        return "B"
    if score >= 0.50:
        return "C"
    return "D"

def main():
    rows = load_rows()
    grouped = group_rows(rows)

    markets = []
    for name, arr in grouped.items():
        tail = arr[-6:]

        confirmations = 0
        series = []

        for r in tail:
            vals = [float(r.get(f, 0) or 0) for f in FIELDS]
            if float(r.get("vacuum_score", 0) or 0) >= 0.15:
                confirmations += 1
            if float(r.get("microstructure_score", 0) or 0) >= 0.04:
                confirmations += 1
            if float(r.get("stale_repricing_score", 0) or 0) >= 0.60:
                confirmations += 1
            series.append(sum(vals))

        persistence = min(len(tail) / 6.0, 1.0)
        stability = max(0.0, 1.0 - min(variance(series), 1.0))
        confirmation_score = min(confirmations / max(len(tail) * 3, 1), 1.0)

        confidence_score = (
            0.35 * persistence +
            0.35 * stability +
            0.30 * confirmation_score
        )

        markets.append({
            "market_name": name,
            "samples": len(tail),
            "persistence": round(persistence, 4),
            "stability": round(stability, 4),
            "confirmation_score": round(confirmation_score, 4),
            "confidence_score": round(confidence_score, 4),
            "confidence_tier": tier(confidence_score),
        })

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets": markets,
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("SIGNAL CONFIDENCE BUILT")
    print("markets:", len(markets))
    print("file: analytics/signal_confidence.json")

if __name__ == "__main__":
    main()
