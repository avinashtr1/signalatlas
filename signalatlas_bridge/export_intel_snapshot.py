import json
import requests
from pathlib import Path
from datetime import datetime, timezone

INTEL_API = "http://127.0.0.1:8011/api/executive"
API_KEY = "sa_7f8c9d1a4b6e2f3c5d0a8e7b9c1d4f6a2v1i2"

OUT = Path("signalatlas_dashboard/intel_snapshot.json")

def main():
    try:
        r = requests.get(
            INTEL_API,
            headers={"x-api-key": API_KEY},
            timeout=5
        )

        data = r.json()

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }

        OUT.write_text(json.dumps(payload, indent=2))
        print("intel snapshot updated")

    except Exception as e:
        print("intel snapshot failed:", e)

if __name__ == "__main__":
    main()
