# SignalAtlas Engine Registry

## Canonical Active Components

### Polymarket Adapter

File:

polymarket_engine/data_adapters/polymarket_adapter.py

Role:

venue normalization and quote semantics

Status:

canonical

---

### Market Raw Collector

File:

polymarket_engine/market_raw_collector.py

Role:

canonical Gamma full-state measurement

Output:

analytics/market_raw.json

analytics/market_measurements.sqlite3

Status:

canonical measurement

---

### Orderbook Collector

File:

polymarket_engine/orderbook_collector.py

Role:

real Polymarket CLOB execution-quality measurement

Output:

analytics/orderbooks.json

analytics/market_measurements.sqlite3

Status:

canonical measurement

---

### Outcome Engine

File:

polymarket_engine/outcome_engine.py

Role:

forward observation labels

Horizons:

1h
6h
24h

Status:

canonical measurement

---

### System Monitor

File:

polymarket_engine/system_monitor.py

Role:

measurement-pipeline observability

Output:

analytics/system_status.json

Status:

canonical measurement

---

### API Server

File:

polymarket_engine/api_server.py

Role:

read-only canonical measurement API

Service:

signalatlas-measurement-api.service

Status:

canonical API

---

# Intelligence Components

Current policy:

do not assume presence means production validity.

Existing intelligence modules must be classified by current semantics before reuse.

---

## Microstructure

Status:

UNSCORED

Current output semantics:

measurement / diagnostics only

No calibrated alpha score exists.

---

## Liquidity Vacuum

Status:

DISABLED

Reason:

awaiting calibration from real CLOB depth history

---

## Resolution Truth

Status:

CANONICAL MEASUREMENT — CERTIFIED / FROZEN V1

Module:

polymarket_engine/resolution_collector.py

Store:

analytics/market_measurements.sqlite3

Tables:

resolution_watch
market_resolutions

Authority:

Polygon Conditional Tokens Framework

Gamma provides market identity and outcome ordering only.

Gamma endDate, closed state, and final-like outcomePrices are not canonical settlement truth.

ConditionResolution event evidence is required before resolution_time_valid can become true.

The prospective timestamp path is implemented and awaits the first newly observed resolution transition in the clean canonical universe.

---

## Resolution Arbitrage

Status:

FAIL-CLOSED

Reason:

canonical settlement truth now exists prospectively, but no calibrated pre-resolution arbitrage model has been validated. Resolution Truth alone does not establish predictive edge.

---

## Structural / NegRisk Analysis

Status:

READ-ONLY ANALYSIS

Only STANDARD_NEGRISK non-augmented groups are structurally eligible.

Basket execution is not implemented.

---

## Brain

Status:

FROZEN / FAIL-CLOSED

Standalone:

reject if no calibrated directional alpha model

Structural members:

reject if basket execution is required

---

# Retired Components

polymarket_engine/intelligence_api.py

polymarket_engine/send_tom_card.py

polymarket_engine/alert_router.py

signalatlas_bridge/export_intel_snapshot.py

Status:

retired / fail-closed

---

# Historical Analytics

Many JSON files remain in analytics/.

Their presence does not imply:

current validity

production use

calibrated intelligence

canonical status

Historical files must not be reintroduced into the active pipeline without explicit audit.
