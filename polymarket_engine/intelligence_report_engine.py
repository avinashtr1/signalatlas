import json
from pathlib import Path
from datetime import datetime, timezone

REGIME = Path("analytics/market_regime_live.json")
ALPHA = Path("analytics/alpha_fusion_signals.json")
MIS = Path("analytics/mispricing_signals.json")
COL = Path("analytics/liquidity_collapse_signals.json")
MOM = Path("analytics/momentum_break_signals.json")

OUT = Path("analytics/intelligence_report.txt")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():

    regime = load_json(REGIME)
    alpha = load_json(ALPHA)
    mis = load_json(MIS)
    col = load_json(COL)
    mom = load_json(MOM)

    env = regime.get("regime", "unknown")

    top_alpha = alpha.get("signals", [])[:3]
    mis_count = mis.get("count", 0)
    col_count = col.get("count", 0)
    mom_count = mom.get("count", 0)

    lines = []

    lines.append("📡 SIGNALATLAS INTELLIGENCE REPORT\n")
    lines.append(f"Environment: {env}\n")

    lines.append("TOP ALPHA SIGNALS\n")

    if not top_alpha:
        lines.append("No high quality signals detected\n")
    else:
        for i, s in enumerate(top_alpha, 1):
            lines.append(
                f"{i}. {s.get('market_name')} "
                f"(Alpha {round(s.get('alpha_score',0),3)})"
            )

    lines.append("\n")

    lines.append(f"Mispricing Signals: {mis_count}")
    lines.append(f"Liquidity Collapse Signals: {col_count}")
    lines.append(f"Momentum Break Signals: {mom_count}")

    lines.append("\nGenerated: " + datetime.now(timezone.utc).isoformat())

    report = "\n".join(lines)

    OUT.write_text(report, encoding="utf-8")

    print("INTELLIGENCE REPORT BUILT")
    print("file:", OUT)
    print("\n--- REPORT PREVIEW ---\n")
    print(report)

if __name__ == "__main__":
    main()
