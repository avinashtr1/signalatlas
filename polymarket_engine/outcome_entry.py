import json
import sys
from pathlib import Path

OUTCOMES_PATH = Path("analytics/market_outcomes.json")

VALID = {"YES", "NO"}

def load_json(path):
    if not path.exists():
        return {"outcomes": {}}
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    if len(sys.argv) < 3:
        print('Usage:')
        print('  PYTHONPATH=. python3 -m polymarket_engine.outcome_entry "Market Name" YES')
        print('  PYTHONPATH=. python3 -m polymarket_engine.outcome_entry "Market Name" NO')
        return

    market_name = sys.argv[1].strip()
    outcome = sys.argv[2].strip().upper()

    if outcome not in VALID:
        print("Outcome must be YES or NO")
        return

    data = load_json(OUTCOMES_PATH)
    outcomes = data.setdefault("outcomes", {})
    outcomes[market_name] = outcome

    OUTCOMES_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print("SIGNALATLAS OUTCOME ENTRY")
    print(f"market: {market_name}")
    print(f"outcome: {outcome}")
    print("updated: analytics/market_outcomes.json")

if __name__ == "__main__":
    main()
