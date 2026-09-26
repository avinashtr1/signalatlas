import json
from pathlib import Path
from datetime import datetime, timezone

SRC = Path("analytics/market_universe_clean.json")
OUT = Path("analytics/narrative_clusters.json")

CLUSTERS = {
    "politics": ["election", "president", "senate", "house", "democrat", "republican", "trump", "biden", "government"],
    "crypto": ["bitcoin", "btc", "ethereum", "eth", "solana", "crypto", "token", "defi", "etf"],
    "sports": ["nba", "nfl", "mlb", "nhl", "finals", "championship", "playoffs", "western conference", "eastern conference"],
    "macro": ["fed", "inflation", "rate", "recession", "gdp", "oil", "gold", "economy"],
    "tech": ["openai", "ai", "apple", "tesla", "google", "meta", "nvidia", "microsoft"],
}

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def classify(q):
    ql = (q or "").lower()
    hits = []
    for name, words in CLUSTERS.items():
        score = sum(1 for w in words if w in ql)
        if score > 0:
            hits.append((name, score))
    if not hits:
        return "other"
    hits.sort(key=lambda x: x[1], reverse=True)
    return hits[0][0]

def main():
    doc = load_json(SRC)
    markets = doc.get("markets", [])

    clusters = {}
    for m in markets:
        q = m.get("question") or ""
        c = classify(q)
        clusters.setdefault(c, []).append(m)

    out_clusters = []
    for name, items in clusters.items():
        items = sorted(items, key=lambda x: (x.get("volume", 0), x.get("liquidity", 0)), reverse=True)
        out_clusters.append({
            "cluster": name,
            "count": len(items),
            "top_markets": items[:25]
        })

    out_clusters.sort(key=lambda x: x["count"], reverse=True)

    OUT.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(out_clusters),
        "clusters": out_clusters
    }, indent=2), encoding="utf-8")

    print("NARRATIVE CLUSTER ENGINE BUILT")
    print("clusters:", len(out_clusters))
    for c in out_clusters[:10]:
        print(c["cluster"], c["count"])

if __name__ == "__main__":
    main()
