import json
from pathlib import Path
from datetime import datetime, timezone

SRC = Path("analytics/signal_memory.json")
OUT = Path("analytics/opportunity_ranking.json")
REGIME_FILE = Path("analytics/market_regime_live.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def get_regime():
    data = load_json(REGIME_FILE)
    return data.get("regime", "calm")

def main():
    mem = load_json(SRC).get("rows", [])
    regime = get_regime()

    ranked = []

    for r in mem[-300:]:
        alpha_score = float(r.get("alpha_score", 0) or 0)
        mispricing_edge = float(r.get("mispricing_edge", 0) or 0)
        collapse_score = float(r.get("collapse_score", 0) or 0)

        if regime == "volatile":
            score = alpha_score * 0.4 + mispricing_edge * 0.4 + collapse_score * 0.2
        elif regime == "trending":
            score = alpha_score * 0.5 + mispricing_edge * 0.3 + collapse_score * 0.2
        elif regime == "illiquid":
            score = alpha_score * 0.3 + mispricing_edge * 0.2 + collapse_score * 0.5
        else:
            score = alpha_score * 0.6 + mispricing_edge * 0.3 + collapse_score * 0.1

        ranked.append({
            "market_name": r.get("market_name"),
            "alpha_score": alpha_score,
            "mispricing_edge": mispricing_edge,
            "collapse_score": collapse_score,
            "opportunity_score": round(score, 6)
        })

    ranked.sort(key=lambda x: x["opportunity_score"], reverse=True)

    # deduplicate by market_name, keep highest-ranked first
    seen = set()
    unique = []
    for r in ranked:
        name = r.get("market_name")
        if not name or name in seen:
            continue
        seen.add(name)
        unique.append(r)

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets_ranked": len(unique),
        "top_opportunities": unique[:10]
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("OPPORTUNITY RANKER BUILT")
    print("file:", OUT)
    print("markets ranked:", len(unique))

if __name__ == "__main__":
    main()
