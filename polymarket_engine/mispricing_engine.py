import json
from pathlib import Path
from datetime import datetime, timezone

SRC = Path("analytics/market_universe_clean.json")
OUT = Path("analytics/mispricing_signals.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def save_json(p,d):
    p.write_text(json.dumps(d,indent=2))

def estimate_probability(m):
    q = (m.get("question") or "").lower()

    base = 0.5

    if "win" in q:
        base = 0.45
    if "will" in q:
        base = 0.52
    if "increase" in q:
        base = 0.48

    return base

def market_probability(m):
    vol = float(m.get("volume") or 0)

    if vol > 1_000_000_000:
        return 0.55
    if vol > 100_000_000:
        return 0.52
    if vol > 10_000_000:
        return 0.50

    return 0.48

def main():

    data = load_json(SRC)
    markets = data.get("markets",[])

    signals = []

    for m in markets:

        mp = market_probability(m)
        ep = estimate_probability(m)

        edge = ep - mp

        if abs(edge) > 0.03:

            signals.append({
                "question": m.get("question"),
                "market_probability": mp,
                "model_probability": ep,
                "alpha": edge
            })

    save_json(OUT,{
        "timestamp":datetime.now(timezone.utc).isoformat(),
        "signals":signals
    })

    print("MISPRICING ENGINE BUILT")
    print("signals:",len(signals))

if __name__ == "__main__":
    main()
