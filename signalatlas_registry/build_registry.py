import json
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path("/root/.openclaw/workspace")
REG = ROOT / "signalatlas_registry"
ENGINE_DIR = ROOT / "polymarket_engine"
ANALYTICS_DIR = ROOT / "analytics"
DASHBOARD_DIR = ROOT / "signalatlas_dashboard"

API_FILE = ENGINE_DIR / "api_server.py"
MEASUREMENT_DB = ANALYTICS_DIR / "market_measurements.sqlite3"
HEALTH_FILE = ANALYTICS_DIR / "system_status.json"


COMPONENT_STATUS = {
    "market_raw_collector": "canonical_measurement",
    "orderbook_collector": "canonical_measurement",
    "outcome_engine": "canonical_measurement",
    "system_monitor": "canonical_measurement",
    "api_server": "canonical_api",

    "intelligence_api": "retired_fail_closed",
    "send_tom_card": "retired_fail_closed",
    "alert_router": "retired_fail_closed",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def list_py_files(p):
    if not p.exists():
        return []
    return sorted(
        str(x.relative_to(ROOT))
        for x in p.glob("*.py")
    )


def list_html_files(p):
    if not p.exists():
        return []
    return sorted(
        str(x.relative_to(ROOT))
        for x in p.glob("*.html")
    )


def list_json_files(p):
    if not p.exists():
        return []
    return sorted(
        str(x.relative_to(ROOT))
        for x in p.glob("*.json")
    )


def build_engine_registry():
    files = list_py_files(ENGINE_DIR)
    engines = []

    for f in files:
        name = Path(f).stem
        engines.append({
            "name": name,
            "file": f,
            "status": COMPONENT_STATUS.get(
                name,
                "present_unclassified",
            ),
        })

    return {
        "timestamp": now(),
        "count": len(engines),

        "canonical_measurement_pipeline": [
            "polymarket_engine/market_raw_collector.py",
            "polymarket_engine/orderbook_collector.py",
            "polymarket_engine/outcome_engine.py",
            "polymarket_engine/system_monitor.py",
        ],

        "canonical_api": "polymarket_engine/api_server.py",

        "legacy_retired": [
            "polymarket_engine/intelligence_api.py",
            "polymarket_engine/send_tom_card.py",
            "polymarket_engine/alert_router.py",
            "signalatlas_bridge/export_intel_snapshot.py",
        ],

        "engines": engines,
    }


def build_dashboard_registry():
    pages = list_html_files(DASHBOARD_DIR)

    return {
        "timestamp": now(),

        "public_shell_port": 8020,

        "pages_count": len(pages),
        "pages": pages,

        "known_pages": {
            "terminal": "signalatlas_dashboard/index.html",
            "history": "signalatlas_dashboard/history.html",
            "ops": "signalatlas_dashboard/ops.html",
            "heatmap": "signalatlas_dashboard/heatmap.html",
            "clusters": "signalatlas_dashboard/clusters.html",
        },

        "canonical_api": {
            "host": "127.0.0.1",
            "port": 8011,
            "exposure": "localhost_only",
            "mode": "read_only",
            "service_unit":
                "signalatlas-measurement-api.service",
        },
    }


def build_analytics_registry():
    files = list_json_files(ANALYTICS_DIR)

    return {
        "timestamp": now(),
        "count": len(files),
        "files": files,

        "canonical_measurement_store": {
            "file":
                "analytics/market_measurements.sqlite3",
            "exists":
                MEASUREMENT_DB.exists(),
            "size_bytes":
                MEASUREMENT_DB.stat().st_size
                if MEASUREMENT_DB.exists()
                else None,
        },

        "canonical_artifacts": {
            "latest_market_snapshot":
                "analytics/market_raw.json",
            "latest_clob_snapshot":
                "analytics/orderbooks.json",
            "measurement_health":
                "analytics/system_status.json",
        },

        "historical_or_legacy_analytics_present": True,
        "note": (
            "Presence in analytics/ does not imply canonical "
            "or currently active intelligence."
        ),
    }


def extract_routes():
    if not API_FILE.exists():
        return []

    txt = API_FILE.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    routes = []

    for line in txt.splitlines():
        line = line.strip()

        if line.startswith("@app.get("):
            routes.append(line)

    return routes


def build_api_registry():
    routes = extract_routes()

    return {
        "timestamp": now(),

        "status": "canonical_active",

        "api_file":
            str(API_FILE.relative_to(ROOT))
            if API_FILE.exists()
            else None,

        "service_unit":
            "signalatlas-measurement-api.service",

        "bind_host": "127.0.0.1",
        "port": 8011,
        "exposure": "localhost_only",
        "mode": "read_only",

        "backing_store":
            "analytics/market_measurements.sqlite3",

        "health_artifact":
            "analytics/system_status.json",

        "source_scope": {
            "complete_universe": False,
            "coverage": "partial_event_slice",
        },

        "routes_count": len(routes),
        "routes": routes,

        "allowed_capabilities": [
            "read_measurement_health",
            "read_latest_markets",
            "read_market_snapshot",
            "read_clob_measurement",
            "read_market_history",
            "read_forward_outcomes",
        ],

        "excluded_capabilities": [
            "shell_execution",
            "trade_execution",
            "pipeline_execution",
            "legacy_alpha_feed",
            "legacy_radar",
            "legacy_profit_simulation",
        ],

        "legacy_api": {
            "file":
                "polymarket_engine/intelligence_api.py",
            "status":
                "retired_fail_closed",
            "former_port":
                8011,
        },
    }


def build_telegram_registry():
    files = list_py_files(ENGINE_DIR)

    tg_related = [
        f for f in files
        if any(
            k in f
            for k in [
                "send_",
                "alert",
                "feed",
                "telegram",
                "shock",
            ]
        )
    ]

    return {
        "timestamp": now(),

        "status":
            "legacy_distribution_not_canonical",

        "known_channels": [
            "SignalAtlas Market Radar",
            "Signal Atlas Pro",
        ],

        "known_env": [
            "TG_BOT_TOKEN",
            "TG_PUBLIC_CHAT_ID",
            "TG_PRO_CHAT_ID",
        ],

        "related_files":
            tg_related,

        "note": (
            "Telegram/distribution modules are not part of "
            "the canonical measurement pipeline."
        ),
    }


def main():
    REG.mkdir(exist_ok=True)

    write_json(
        REG / "ENGINE_REGISTRY.json",
        build_engine_registry(),
    )

    write_json(
        REG / "DASHBOARD_REGISTRY.json",
        build_dashboard_registry(),
    )

    write_json(
        REG / "ANALYTICS_REGISTRY.json",
        build_analytics_registry(),
    )

    write_json(
        REG / "API_REGISTRY.json",
        build_api_registry(),
    )

    write_json(
        REG / "TELEGRAM_REGISTRY.json",
        build_telegram_registry(),
    )

    print("SIGNALATLAS REGISTRY BUILT")
    print(
        "engine registry:",
        REG / "ENGINE_REGISTRY.json",
    )
    print(
        "api registry:",
        REG / "API_REGISTRY.json",
    )
    print(
        "dashboard registry:",
        REG / "DASHBOARD_REGISTRY.json",
    )
    print(
        "telegram registry:",
        REG / "TELEGRAM_REGISTRY.json",
    )
    print(
        "analytics registry:",
        REG / "ANALYTICS_REGISTRY.json",
    )


if __name__ == "__main__":
    main()
