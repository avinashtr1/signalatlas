import json
from pathlib import Path
from datetime import datetime

BASE = Path("analytics")
OUT = BASE / "market_shocks.json"

def load(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def save(p,d):
    p.write_text(json.dumps(d,indent=2))

def main():

    radar = load(BASE / "opportunity_ranking.json")
    shocks = []

    for r in radar.get("ranked",[])[:50]:

        score = r.get("opportunity_score",0)
        urgency = r.get("execution_urgency",0)

        if score > 0.35 or urgency > 0.6:

            shocks.append({
                "market": r["market_name"],
                "score": score,
                "urgency": urgency,
                "timestamp": datetime.now().isoformat()
            })

    save(OUT,{
        "timestamp":datetime.now().isoformat(),
        "count":len(shocks),
        "shocks":shocks
    })

    print("SHOCK DETECTOR BUILT")
    print("shocks:",len(shocks))

if __name__=="__main__":
    main()
