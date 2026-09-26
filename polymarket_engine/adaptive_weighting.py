import json
from pathlib import Path
from datetime import datetime, timezone

MODULE_SCORING_PATH = Path("analytics/module_scoring.json")
OUT_JSON = Path("analytics/adaptive_weights.json")
OUT_TXT = Path("analytics/adaptive_weights.txt")

BASELINE = {
    "quality": 0.30,
    "vacuum": 0.25,
    "microstructure": 0.20,
    "stale_repricing": 0.25,
}

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def normalize(weights):
    s = sum(weights.values()) or 1.0
    return {k: v / s for k, v in weights.items()}

def main():
    data = load_json(MODULE_SCORING_PATH)
    modules = data.get("modules", [])

    score_map = {m["module"]: float(m.get("avg_score", 0.0) or 0.0) for m in modules}

    raw = {}
    for module, base in BASELINE.items():
        raw[module] = base * (1.0 + score_map.get(module, 0.0))

    normalized = normalize(raw)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rows": data.get("rows", 0),
        "baseline": BASELINE,
        "module_scores": score_map,
        "adaptive_weights": {k: round(v, 6) for k, v in normalized.items()},
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS ADAPTIVE WEIGHTS")
    lines.append("")
    for k, v in payload["adaptive_weights"].items():
        lines.append(f"{k}: {v:.3f}")
    lines.append("")
    lines.append("MODULE SCORES")
    for k, v in score_map.items():
        lines.append(f"{k}: {v:.3f}")

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/adaptive_weights.json")
    print("analytics/adaptive_weights.txt")

if __name__ == "__main__":
    main()
