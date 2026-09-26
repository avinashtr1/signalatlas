# SignalAtlas API Registry

## Canonical API

Module:

polymarket_engine/api_server.py

Service:

signalatlas-measurement-api.service

Bind:

127.0.0.1:8011

Exposure:

localhost only

Mode:

read-only

Backing store:

analytics/market_measurements.sqlite3

---

## Current Routes

GET /

GET /api/health

GET /api/meta

GET /api/markets

GET /api/market/{market_id}

GET /api/orderbook/{market_id}

GET /api/measurements/{market_id}

GET /api/forward-outcomes/{market_id}

GET /api/resolution-status/{market_id}

GET /api/resolution/{market_id}

GET /api/resolutions

OpenAPI:

GET /openapi.json

Docs:

GET /docs

---

## Current Scope

Measurement scope:

complete_universe = false

coverage = partial_event_slice

Current snapshot, CLOB, measurement-history, and forward-outcome collection is a bounded active-event slice.

Resolution Truth scope:

complete_universe = false

coverage = historically_observed_signalatlas_markets

resolution_watch tracks every historically observed SignalAtlas market.

market_resolutions contains immutable CTF settlement truth when a tracked market resolves.

Resolution coverage is therefore broader than the current active measurement slice, but neither scope represents the complete Polymarket universe.

---

## Allowed Capabilities

read measurement health

read current canonical markets

read canonical market snapshots

read real CLOB measurements

read historical observations

read forward outcomes

read API authority / freshness metadata

read mutable resolution tracking status

read immutable on-chain market resolution truth

list immutable resolution records

---

## Forbidden / Absent Capabilities

shell execution

pipeline execution

trade execution

capital allocation

Brain decisioning

event-measurement API exposure during the frozen prospective experiment

legacy alpha feed

legacy radar

legacy profit simulation

legacy Tom orchestration

---

## Legacy API

Module:

polymarket_engine/intelligence_api.py

Status:

RETIRED / FAIL-CLOSED

Former port:

8011

The legacy API must not be restarted.

It previously exposed stale heuristic outputs and command-execution endpoints.

---

## Future API Direction

REST / OpenAPI remains canonical.

Later surfaces may include:

Python SDK

agent tools / MCP

authenticated sandbox execution intents

permissioned live execution intents

All execution capabilities must remain downstream of risk and permission controls.
