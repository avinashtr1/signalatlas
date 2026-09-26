# SignalAtlas Master Roadmap

## Vision

SignalAtlas = prediction-market intelligence infrastructure.

Long-term product:

70% Bloomberg Terminal
+
30% Nansen Analytics

for prediction markets.

Primary machine customer:

AI agents

Human operators remain important, but APIs and deterministic schemas are first-class architecture.

---

# PHASE 1 — Measurement Foundation

Status:

ACTIVE / FOUNDATION BUILT

Completed:

- repaired Polymarket adapter
- canonical snapshot measurement
- real Gamma top-of-book semantics
- real CLOB depth collection
- durable SQLite measurement history
- 1h / 6h / 24h forward outcome framework
- measurement health
- canonical Polygon CTF resolution truth — v1 certified / frozen
- canonical read-only OpenAPI
- legacy heuristic API retired
- old paper runtime retired
- Brain frozen fail-closed

Current requirement:

accumulate clean forward data before rebuilding alpha.

---

# PHASE 2 — Calibrated Intelligence

Status:

PENDING DATA

Candidate research areas:

- directional probability models
- microstructure
- liquidity / execution quality
- probability drift / repricing
- standard NegRisk basket economics
- cross-market relationships
- narrative clustering

Requirement:

models must be evidence-driven and calibrated against collected outcomes.

Execution-sensitive research must use net executable economics: same-share quantity, measured book depth, and applicable market-specific fees. Gross price movement alone is not a valid economic target.

No heuristic may be promoted to production alpha without validation.

---

# PHASE 3 — Brain / Portfolio Intelligence

Status:

FROZEN

Future responsibilities:

- signal evaluation
- confidence calibration
- opportunity ranking
- portfolio allocation
- risk-aware capital budgeting

Current Brain remains fail-closed until calibrated intelligence exists.

---

# PHASE 4 — Operator Terminal

Professional prediction-market workstation.

Potential surfaces:

- market explorer
- measurement history
- orderbook / liquidity analytics
- intelligence views
- structural-market analysis
- portfolio / execution monitoring

UI remains downstream of APIs.

---

# PHASE 5 — Agent Intelligence API

Status:

FOUNDATION ACTIVE

Expose deterministic prediction-market intelligence to AI agents.

Currently implemented:

read markets
read measurements
read CLOB state
read forward-outcome history
read API authority / freshness metadata
read resolution tracking status
read immutable on-chain settlement truth
read resolution event evidence when available

Not yet available:

calibrated signals
event-measurement API exposure

Later:

submit execution intents
request simulations
query portfolio state

Agents do not receive unrestricted trading authority.

---

# PHASE 6 — Distribution / Commercial Intelligence

Possible products:

SignalAtlas Radar
private alpha feed
professional API
institutional terminal
research feeds

Commercial distribution follows validated intelligence.

---

# PHASE 7 — Strategy Infrastructure

Validated strategies may become deployable through VelocityAtlas.

Possible models:

directional
structural basket
cross-market
execution / liquidity
event-driven

All execution remains permissioned and risk-controlled.

---

# PHASE 8 — Agent Execution Layer

SignalAtlas:

intelligence infrastructure

VelocityAtlas:

permissioned execution infrastructure

Agent flow:

observe
→ reason
→ submit intent
→ validate risk
→ validate execution
→ execute
→ reconcile
→ audit

---

# Current Moat Being Built

The immediate moat is not a dashboard or heuristic signal feed.

It is:

clean historical market state

+
real execution-quality CLOB data

+
forward outcome labels

+
strict structural semantics

+
fail-closed intelligence

+
agent-ready deterministic interfaces

---

# Current Priority

Do not optimize presentation.

Do not revive legacy alpha.

Do not re-enable the old feed.

Do not modify the Brain without evidence.

Collect clean data first.

Then:

measure
→ diagnose
→ model
→ validate
→ deploy
