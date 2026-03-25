import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/root/.openclaw/workspace")
REG = ROOT / "signalatlas_registry"
ENGINE_DIR = ROOT / "polymarket_engine"
ANALYTICS_DIR = ROOT / "analytics"
DASHBOARD_DIR = ROOT / "signalatlas_dashboard"

def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def list_py_files(p):
    if not p.exists():
        return []
    return sorted([str(x.relative_to(ROOT)) for x in p.glob("*.py")])

def list_html_files(p):
    if not p.exists():
        return []
    return sorted([str(x.relative_to(ROOT)) for x in p.glob("*.html")])

def list_json_files(p):
    if not p.exists():
        return []
    return sorted([str(x.relative_to(ROOT)) for x in p.glob("*.json")])

def build_engine_registry():
    files = list_py_files(ENGINE_DIR)
    engines = []
    for f in files:
        name = Path(f).stem
        engines.append({
            "name": name,
            "file": f,
            "status": "present"
        })
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(engines),
        "engines": engines
    }

def build_dashboard_registry():
    pages = list_html_files(DASHBOARD_DIR)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "public_shell_port": 8020,
        "pages_count": len(pages),
        "pages": pages,
        "known_pages": {
            "terminal": "signalatlas_dashboard/index.html",
            "history": "signalatlas_dashboard/history.html",
            "ops": "signalatlas_dashboard/ops.html",
            "heatmap": "signalatlas_dashboard/heatmap.html",
            "clusters": "signalatlas_dashboard/clusters.html"
        },
        "internal_console": {
            "dashboard_port": 8022,
            "api_port": 8011
        }
    }

def build_analytics_registry():
    files = list_json_files(ANALYTICS_DIR)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(files),
        "files": files
    }

def build_api_registry():
    api_file = ENGINE_DIR / "api_server.py"
    routes = []
    if api_file.exists():
        txt = api_file.read_text(encoding="utf-8", errors="ignore")
        for line in txt.splitlines():
            line = line.strip()
            if line.startswith("@app.get("):
                routes.append(line)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api_file": str(api_file.relative_to(ROOT)) if api_file.exists() else None,
        "routes_count": len(routes),
        "routes": routes
    }

def build_telegram_registry():
    files = list_py_files(ENGINE_DIR)
    tg_related = [f for f in files if any(k in f for k in [
        "send_", "alert", "feed", "telegram", "shock"
    ])]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "known_channels": [
            "SignalAtlas Market Radar",
            "Signal Atlas Pro"
        ],
        "known_env": [
            "TG_BOT_TOKEN",
            "TG_PUBLIC_CHAT_ID",
            "TG_PRO_CHAT_ID"
        ],
        "related_files": tg_related
    }

def main():
    REG.mkdir(exist_ok=True)

    write_json(REG / "ENGINE_REGISTRY.json", build_engine_registry())
    write_json(REG / "DASHBOARD_REGISTRY.json", build_dashboard_registry())
    write_json(REG / "ANALYTICS_REGISTRY.json", build_analytics_registry())
    write_json(REG / "API_REGISTRY.json", build_api_registry())
    write_json(REG / "TELEGRAM_REGISTRY.json", build_telegram_registry())

    print("SIGNALATLAS REGISTRY BUILT")
    print("engine registry:", REG / "ENGINE_REGISTRY.json")
    print("api registry:", REG / "API_REGISTRY.json")
    print("dashboard registry:", REG / "DASHBOARD_REGISTRY.json")
    print("telegram registry:", REG / "TELEGRAM_REGISTRY.json")
    print("analytics registry:", REG / "ANALYTICS_REGISTRY.json")

if __name__ == "__main__":
    main()
