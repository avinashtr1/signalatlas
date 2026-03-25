import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path("analytics")
INTEL = BASE / "resolution_intelligence.json"
REGIME = BASE / "market_regime.json"
OUT = BASE / "adaptive_weight_trainer.json"

BASELINE = {
    "vacuum": 0.25,
    "microstructure": 0.20,
    "stale_repricing": 0.20,
    "resolution_arb": 0.20,
    "liquidity_collapse": 0.10,
    "shock": 0.05,
}

MAP_INTEL_TO_WEIGHT = {
    "vacuum": "vacuum",
    "microstructure": "microstructure",
    "stale_repricing": "stale_repricing",
    "resolution_arb": "resolution_arb",
    "collapse": "liquidity_collapse",
    "shock": "shock",
}

def load_json(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def normalize(d):
    s = sum(d.values()) or 1.0
    return {k: v / s for k, v in d.items()}

def main():
    intel = load_json(INTEL).get("module_performance", {})
    regime = load_json(REGIME)
    active_regime = regime.get("active_regime", "unknown")

    multipliers = {}
    diagnostics = {}

    for intel_key, weight_key in MAP_INTEL_TO_WEIGHT.items():
        row = intel.get(intel_key, {})
        win_rate = float(row.get("win_rate", 0.0) or 0.0)
        total = int(row.get("total", 0) or 0)

        # confidence shrinks tiny samples toward neutral
        confidence = clamp(total / 30.0, 0.0, 1.0)

        # neutral center at 0.50 win rate
        learned = 1.0 + ((win_rate - 0.50) * 1.2 * confidence)

        # keep trainer conservative
        learned = clamp(learned, 0.70, 1.30)

        multipliers[weight_key] = learned
        diagnostics[weight_key] = {
            "win_rate": round(win_rate, 4),
            "total": total,
            "confidence": round(confidence, 4),
            "multiplier": round(learned, 4),
        }

    raw = {
        k: BASELINE[k] * multipliers.get(k, 1.0)
        for k in BASELINE
    }
    trained_weights = normalize(raw)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_regime": active_regime,
        "baseline": BASELINE,
        "trainer_diagnostics": diagnostics,
        "trained_weights": {k: round(v, 6) for k, v in trained_weights.items()},
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("ADAPTIVE WEIGHT TRAINER")
    print(f"active_regime: {active_regime}")
    for k, v in payload["trained_weights"].items():
        print(f"{k}: {v:.3f}")
    print("")
    print("file created: analytics/adaptive_weight_trainer.json")

if __name__ == "__main__":
    main()
