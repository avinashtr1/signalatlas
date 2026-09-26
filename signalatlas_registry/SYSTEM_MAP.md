# SignalAtlas System Map

## Product Role

SignalAtlas is prediction-market intelligence infrastructure.

Current priority:

Data truth
→ Measurement
→ Forward outcomes
→ Health
→ Read-only API
→ Calibrated intelligence later

VelocityAtlas remains the separate permissioned execution layer.

---

## Canonical Data / Measurement Flow

Polymarket Gamma
→ PolymarketAdapter
→ market_raw_collector
→ canonical snapshot measurements

Polymarket CLOB
→ orderbook_collector
→ real executable-book measurements

Canonical snapshot history
→ outcome_engine
→ 1h / 6h / 24h forward outcomes

Measurement database
→ system_monitor
→ measurement health

Observed market identity + Polymarket Gamma metadata
→ resolution_collector
→ Polygon Conditional Tokens Framework
→ resolution_watch
→ immutable market_resolutions

Measurement database
→ api_server
→ localhost read-only OpenAPI interface

---

## Canonical Measurement Store

File:

analytics/market_measurements.sqlite3

Tables:

- snapshots
- clob_books
- clob_collection_runs
- event_measurements
- forward_outcomes
- resolution_watch
- market_resolutions

Current collection scope:

partial active-event slice

complete_universe = false

Do not interpret the current dataset as complete Polymarket coverage.

---

## Measurement Schedule

Gamma snapshots:

:01 / :16 / :31 / :46

CLOB depth:

:02 / :17 / :32 / :47

Forward outcomes:

:04 / :19 / :34 / :49

Measurement health:

:06 / :21 / :36 / :51

Resolution truth:

:08 / :23 / :38 / :53

resolution_collector uses adaptive per-market polling internally. Running the collector every 15 minutes does not imply every market is queried every 15 minutes.

Gamma endDate is a scheduling hint only. Polygon CTF is settlement authority.

Current canonical sequence:

:01 snapshots
→ :02 CLOB + event measurements
→ :04 forward outcomes
→ :06 measurement health
→ :08 resolution truth

---

## Canonical API

Service:

signalatlas-measurement-api.service

Module:

polymarket_engine/api_server.py

Bind:

127.0.0.1:8011

Mode:

read-only

Backing store:

analytics/market_measurements.sqlite3

API version:

2.1.0

Current deterministic truth surfaces include:

- measurement health
- current market measurements
- CLOB execution measurements
- measurement history
- forward outcomes
- API authority / freshness metadata
- resolution watch status
- immutable CTF settlement records
- resolution event evidence when available

Measurement API coverage remains a partial active-event slice.

Resolution Truth coverage includes every historically observed SignalAtlas market tracked in resolution_watch.

Neither scope represents complete Polymarket universe coverage.

No shell execution.
No trading actions.
No legacy alpha/radar outputs.

---

## Legacy Intelligence Surface

polymarket_engine/intelligence_api.py

Status:

RETIRED / FAIL-CLOSED

Former behavior included stale heuristic intelligence and command execution.

The legacy feed pipeline remains disabled.

---

## Brain

Current state:

FAIL-CLOSED / FROZEN

The Brain does not emit deployable signals.

Standalone markets reject because no calibrated directional alpha model exists.

Structural NegRisk members reject because basket execution is not implemented.

No synthetic fill, slippage, liquidity, microstructure, or fee assumptions may be used as trading truth.

Execution-quality research uses same-share entry/exit economics, observed book depth, and actual per-market fee configuration where available.

A positive raw price gap or fixed-notional VWAP gap is not canonical economic edge.

The canonical economic measurement is net executable PnL after applicable measured execution costs. Zero taker rebate is the baseline research assumption.

This economic measurement does not imply calibrated alpha or Brain eligibility.

---

## Execution

VelocityAtlas is separate from SignalAtlas measurement infrastructure.

SignalAtlas API currently has no trade execution capability.

VelocityAtlas live execution remains independently controlled.

---

## Dashboard / Distribution

Existing dashboard and Telegram artifacts may still exist historically.

They are not canonical sources of intelligence.

Business logic must not live in dashboards, feeds, Telegram, or presentation code.

---

## Current Architecture

Data
→ Measurement
→ Outcomes
→ Health
→ API

Future:

Data
→ Measurement
→ Calibrated Intelligence
→ Brain
→ Risk / Execution
→ Analytics
→ API / Distribution
