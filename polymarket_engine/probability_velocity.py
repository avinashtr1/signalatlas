import json
from pathlib import Path
from datetime import datetime

BASE = Path("analytics")
OUT = BASE / "probability_velocity.json"

def load(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def save(p,d):
    p.write_text(json.dumps(d,indent=2))

def main():

    radar = load(BASE / "opportunity_ranking.json")

    signals = []

    for r in radar.get("ranked",[])[:100]:

        score = r.get("opportunity_score",0)
        ev = r.get("expected_value",0)

        velocity = score * ev

        if velocity > 0.02:

            signals.append({
                "market": r["market_name"],
                "velocity": velocity,
                "score": score,
                "expected_value": ev,
                "timestamp": datetime.now().isoformat()
            })

    save(OUT,{
        "timestamp":datetime.now().isoformat(),
        "count":len(signals),
        "signals":signals
    })

    print("PROBABILITY VELOCITY ENGINE BUILT")
    print("signals:",len(signals))

if __name__=="__main__":
    main()
