import json
from pathlib import Path
from datetime import datetime, timezone

RADAR = Path("analytics/radar_live.json")
ALERTS = Path("analytics/radar_alerts.json")
LEADERBOARD = Path("analytics/alpha_leaderboard.json")

OUT = Path("analytics/system_status.json")

def load(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def main():

    radar = load(RADAR)
    alerts = load(ALERTS)
    board = load(LEADERBOARD)

    deploy = radar.get("deploy", [])
    watch = radar.get("watch", [])

    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "deploy_now": len(deploy),
        "watchlist": len(watch),
        "total_alerts": len(alerts.get("alerts", [])),
        "alpha_rows": len(board.get("leaderboard", []))
    }

    OUT.write_text(json.dumps(status, indent=2))
    print("SYSTEM STATUS")
    print(status)

if __name__ == "__main__":
    main()
