import json
from pathlib import Path
from datetime import datetime, timezone

REGIME_PATH = Path("analytics/market_regime.json")
OUT_JSON = Path("analytics/regime_adaptive_weights.json")
OUT_TXT = Path("analytics/regime_adaptive_weights.txt")

BASELINE = {
    "vacuum": 0.25,
    "microstructure": 0.20,
    "stale_repricing": 0.20,
    "resolution_arb": 0.20,
    "liquidity_collapse": 0.10,
    "shock": 0.05,
}

REGIME_MAP = {
    "calm": {
        "vacuum": 0.90,
        "microstructure": 0.95,
        "stale_repricing": 1.10,
        "resolution_arb": 1.15,
        "liquidity_collapse": 0.70,
        "shock": 0.70,
    },
    "volatile": {
        "vacuum": 1.10,
        "microstructure": 1.15,
        "stale_repricing": 0.95,
        "resolution_arb": 0.90,
        "liquidity_collapse": 1.25,
        "shock": 1.20,
    },
    "thin_liquidity": {
        "vacuum": 1.20,
        "microstructure": 1.05,
        "stale_repricing": 0.95,
        "resolution_arb": 0.85,
        "liquidity_collapse": 1.35,
        "shock": 0.90,
    },
    "resolution_phase": {
        "vacuum": 0.95,
        "microstructure": 0.90,
        "stale_repricing": 1.00,
        "resolution_arb": 1.35,
        "liquidity_collapse": 0.80,
        "shock": 1.00,
    },
    "event_spike": {
        "vacuum": 1.05,
        "microstructure": 1.00,
        "stale_repricing": 0.90,
        "resolution_arb": 0.90,
        "liquidity_collapse": 1.10,
        "shock": 1.50,
    },
}

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def normalize(d):
    s = sum(d.values()) or 1.0
    return {k: v / s for k, v in d.items()}

def main():
    regime_doc = load_json(REGIME_PATH)
    active = regime_doc.get("active_regime", "calm")
    multipliers = REGIME_MAP.get(active, REGIME_MAP["calm"])

    raw = {k: BASELINE[k] * multipliers[k] for k in BASELINE}
    final = normalize(raw)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_regime": active,
        "baseline": BASELINE,
        "multipliers": multipliers,
        "adaptive_weights": {k: round(v, 6) for k, v in final.items()},
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "SIGNALATLAS REGIME ADAPTIVE WEIGHTS",
        "",
        f"Active Regime: {active}",
        "",
    ]
    for k, v in final.items():
        lines.append(f"{k}: {v:.3f}")

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/regime_adaptive_weights.json")
    print("analytics/regime_adaptive_weights.txt")

if __name__ == "__main__":
    main()
