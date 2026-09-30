# SignalAtlas Master Roadmap v2.0

**Canonical date:** 26 September 2026  
**Status:** Supersedes the original SignalAtlas Master Roadmap

## North Star

SignalAtlas is prediction-market intelligence infrastructure.

The long-term product is a Bloomberg + Nansen-style intelligence platform for prediction markets, serving:

- professional traders
- research desks
- market makers
- funds
- AI agents
- analytics platforms

SignalAtlas must earn the right to produce intelligence by first establishing trustworthy measurement, outcomes, resolution truth and executable economics.

VelocityAtlas remains a separate permissioned execution layer.

EdgeAtlas remains the operator and product interface.

---

## Core Architecture

The canonical dependency chain is:

**Data → Measurement → Outcomes / Resolution Truth → Intelligence → Brain → Risk / Execution → API / Distribution**

Operationally, until calibrated alpha exists:

**Data Truth → Measurement → Forward Outcomes → Resolution Truth → Health → Read-Only API → Research**

No layer may manufacture information that the layer below it has not established.

---

## Permanent Engineering Principles

### Measurement before modeling

Do not infer alpha before proving the underlying measurements.

### Executable economics before signal claims

A theoretical probability difference is not edge.

Canonical economic edge must be based on:

**same-share executable PnL − measured execution costs − applicable fees**

### Prospective evidence before production permission

Historical patterns may generate hypotheses.

They do not automatically authorize Brain decisions.

### Brain is fail-closed

No calibrated model means:

**reject**

not:

**guess**

### CLOB is execution truth

Gamma provides market discovery and metadata.

Executable prices and depth come from the actual order book.

### Settlement truth comes from settlement infrastructure

Market metadata does not substitute for on-chain resolution state.

### SignalAtlas and VelocityAtlas remain separated

SignalAtlas measures and reasons.

VelocityAtlas executes only through explicit permissions and hard risk constraints.

### UI contains no business logic

EdgeAtlas presents canonical system objects and state.

### Every production component must be recoverable

Source, database, configuration, dependencies and services must be reproducible from documented artifacts.

---

## Phase 0 — Truth & Platform Foundation

**Status: MOSTLY COMPLETE / CERTIFIED**

This phase was missing from the original roadmap and has become the foundation for everything that follows.

### 0.1 Canonical Market Data

Completed:

- Polymarket Gamma ingestion
- canonical market normalization
- CanonicalMarket
- canonical snapshot measurement
- invalid pseudo-quote sanitization
- explicit partial-universe scope
- clean 15-minute measurement buckets

Canonical modules:

- `polymarket_adapter.py`
- `market_raw_collector.py`

### 0.2 Executable Order-Book Measurement

Completed:

- public Polymarket CLOB collection
- executable best bid / ask
- book spread
- real depth
- fixed-dollar VWAP measurement
- collector health and coverage
- Gamma/CLOB bucket alignment

Canonical module:

- `orderbook_collector.py`

### 0.3 Forward Outcome Truth

Completed:

- 1h
- 6h
- 24h

forward outcome framework.

Rules:

- exact target buckets
- bounded grace window
- missing data remains missing
- no fabricated labels

Canonical module:

- `outcome_engine.py`

### 0.4 Resolution Truth

**CERTIFIED / FROZEN**

Completed:

Gamma:

- market identity / condition mapping / outcome order

Polygon CTF:

- settlement authority

Canonical state separation:

- `resolution_watch`
- `market_resolutions`

No inferred historical resolution timestamps.

No mutable truth once an immutable resolution has been certified.

### 0.5 Measurement Health

Completed:

- collection freshness
- missing buckets
- CLOB collection state
- Gamma/CLOB alignment
- forward-outcome status
- factual database health

Canonical module:

- `system_monitor.py`

### 0.6 Execution-Economics Calibration

**COMPLETE / FROZEN**

Established that broad taker directional trading is not supported by current evidence after actual execution costs.

Result:

**Brain remains FAIL-CLOSED.**

Future research must prove executable-net economics rather than theoretical price movement.

### 0.7 Canonical Read-Only API

**API v2.1.0 — CERTIFIED / FROZEN**

Architecture:

**SQLite → deterministic canonical objects → REST/OpenAPI → future SDK/MCP/agents**

Current properties:

- read-only
- deterministic
- explicit universe scope
- explicit resolution scope
- no Brain output
- no execution
- no capital allocation
- no experimental event scoring

### 0.8 EdgeAtlas Platform Shell

Completed structurally:

- Markets
- Market detail
- Ops
- Architecture
- Velocity datasets
- health/state visualization
- registry-driven system metadata

Legacy dashboards are retired.

EdgeAtlas remains presentation-only.

### 0.9 Data Durability & Disaster Recovery

**CERTIFIED / FROZEN**

Completed:

- WAL-safe SQLite backups
- hash manifests
- integrity validation
- compressed retention
- autonomous VPS backups
- off-host Windows recovery points
- PC restore drill
- machine recovery pack
- source/dependency/service/config snapshots

### 0.10 Source Control & Release Integrity

**CERTIFIED / FROZEN**

Certified release:

`1942254a9f6f76204d216c1a40b214930d4920e7`

Tag:

`signalatlas-certified-2026-09-26`

Completed:

- generated artifacts removed from Git
- virtualenv removed from Git
- logs/backups excluded
- reproducible API requirements
- legacy paths retired
- complete new Git root
- historical contaminated ancestry disconnected
- full-tree secret scan
- dedicated GitHub deploy key
- canonical main reset to certified root

### Phase 0 Remaining Gate

Before declaring Phase 0 fully closed:

**Clean-VPS Rebuild Rehearsal v1**

Prove a clean machine can reconstruct SignalAtlas from:

- certified Git root
- off-host database backup
- recovery assets
- credential recovery procedure

Also revoke/rotate any legacy credential already considered exposed.

---

## Phase 1 — Calibrated Intelligence Research

**Status: ACTIVE NEXT RESEARCH PHASE**

Goal:

Turn trustworthy measurements into statistically and economically defensible intelligence.

This phase does not begin by re-enabling old signal engines.

It begins with evidence.

### 1.1 Event Measurement Study

Current experiment:

**prospective / frozen**

Checkpoint:

approximately **29 September 2026**

Study:

- event-level market structure
- dispersion
- probability concentration
- two-sidedness
- liquidity
- depth
- imbalance
- CLOB coverage
- short-horizon changes

No tuning during accumulation.

### 1.2 Canonical Universe Expansion

**PRODUCTION-STABLE / FROZEN — 30 September 2026**

Canonical architecture:

**Gamma Discovery → Canonical Universe Index → Lifecycle / Identity Eligibility → CLOB Verification Scheduler → HOT / WARM / COLD Universes → Measurement**

Production state:

- Canonical Universe Index is deployed in `analytics/market_measurements.sqlite3`.
- Canonical discovery completed across 303,014 unique markets.
- 230,231 Gamma-eligible markets received initial CLOB verification coverage.
- CLOB state is established from the CLOB itself rather than Gamma `two_sided`.
- Canonical CLOB states include `TWO_SIDED`, `PARTIAL`, `DEGRADED`, and `UNAVAILABLE`.
- Scheduler tiers are `HOT`, `WARM`, and `COLD`.
- Canonical tier cadences are 30m / 120m / 720m.
- Production scheduler runs every 5 minutes with a 20,000-market run limit.
- Capacity allocation is dynamically weighted from current eligible tier population and canonical tier cadence.
- Unused tier reservation spills into globally oldest due work.
- Market-state writes use 250-market transaction checkpoints.
- Interrupted verifier runs are reconciled explicitly.
- Production steady-state validation showed no HOT or WARM work more than 15 minutes overdue after bootstrap debt cleared.
- Autonomous production runs completed with selected = processed = committed and zero batch failures during the certification window.
- The verifier is measurement infrastructure only. It grants no Brain, signal, execution, or capital-allocation permission.

Canonical modules:

- `universe_scanner.py`
- `universe_clob_verifier.py`

This component is frozen unless new production evidence requires a scheduler or state-machine change.

### 1.3 Intelligence Research Families

Research may examine:

- structural mispricing
- liquidity dislocations
- microstructure
- resolution-state effects
- cross-market relationships
- narrative/event structure
- probability repricing
- event-level regimes

Existing historical engines are hypothesis sources—not production truth.

### 1.4 Research Standards

Every candidate signal must answer:

- What was known at decision time?
- What executable price was actually available?
- What happened prospectively afterward?
- What costs apply?
- Does the effect persist out of sample?
- Does it survive across relevant regimes?

### Phase 1 Exit Gate

A candidate intelligence model may progress only when there is enough evidence to establish:

- clear causal measurement definition
- no look-ahead contamination
- sufficient prospective sample
- repeatability
- economically meaningful effect
- executable-net advantage
- bounded failure modes

Until then:

**no Brain permission**

---

## Phase 2 — Brain Certification & Shadow Decisions

**Status: NOT STARTED**

Goal:

Convert individually certified intelligence models into deterministic decision objects.

The Brain should not become a single global model.

Permissions should be granular.

Examples:

- model
- market class
- event class
- horizon
- liquidity regime
- execution mode

Development sequence:

**Research model → offline evaluation → prospective shadow decisions → monitored paper decisions → certified strategy permission**

Canonical Brain output eventually includes:

- decision
- direction
- expected edge
- evidence provenance
- confidence / uncertainty
- market regime
- execution assumptions
- rejection reason

Every decision must be explainable from canonical inputs.

### Phase 2 Exit Gate

No strategy progresses until:

- shadow behavior matches intended logic
- prospective performance validates research
- executable economics remain positive
- failure states fail closed
- attribution is available
- model/version provenance is recorded

---

## Phase 3 — Paper Portfolio & Risk Validation

**Status: FUTURE**

This replaces the old assumption that merely producing a signal should automatically create a paper trade.

Only certified Brain strategies enter this phase.

Goal:

Measure interaction between multiple individually-valid opportunities.

Research:

- portfolio concentration
- correlated event risk
- strategy overlap
- liquidity limits
- sizing
- drawdown behavior
- execution timing
- position lifecycle
- resolution exposure

Canonical outputs:

`CanonicalTrade`

plus portfolio and strategy attribution.

Paper results remain simulation evidence, not automatically live evidence.

---

## Phase 4 — Operator Intelligence Terminal

**Status: PLATFORM SHELL ALREADY BUILT / INTELLIGENCE ACTIVATION PENDING**

EdgeAtlas already supplies much of the infrastructure.

Once certified intelligence exists, the terminal activates professional decision-support surfaces.

Target capabilities:

- live canonical markets
- executable book state
- event intelligence
- certified opportunities
- signal provenance
- signal confidence
- forward-outcome evidence
- resolution state
- cross-market relationships
- market/event regime
- historical model performance
- strategy state
- system/data health

The terminal should answer:

- What is happening?
- Why does SignalAtlas think it matters?
- What evidence supports it?
- What could invalidate it?
- What is executable now?

This is the Bloomberg side of the product.

Market/entity/network analytics become the Nansen side.

---

## Phase 5 — Intelligence API & Agent Read Layer

**Status: TRANSPORT FOUNDATION COMPLETE / INTELLIGENCE CONTENT PENDING**

The infrastructure exists ahead of schedule.

Future work is not another API rewrite.

It is controlled exposure of certified intelligence.

Potential objects:

- markets
- measurements
- books
- events
- resolutions
- regimes
- signals
- relationships
- opportunity state
- model evidence

Distribution:

**REST/OpenAPI → SDK → MCP / agent tools**

Agents receive deterministic structured information.

Agents do not bypass SignalAtlas validation.

---

## Phase 6 — Commercial Intelligence Products

**Status: DEFERRED UNTIL INTELLIGENCE EXISTS**

The original roadmap moved rapidly toward Telegram alpha feeds.

That order is retired.

Commercialization can begin at multiple levels.

### Data / Intelligence Products

Can eventually include:

- professional terminal
- API access
- market/event intelligence
- resolution intelligence
- historical datasets
- research analytics
- agent feeds

### Certified Alpha Products

Only if evidence justifies them:

- opportunity feeds
- strategy intelligence
- premium alerts
- professional research reports

The product must never label ordinary measurements as alpha simply because they are interesting.

Initial revenue objective may remain:

**$10k MRR**

but revenue must validate product usefulness—not pressure the research layer into premature signal production.

---

## Phase 7 — VelocityAtlas Permissioned Execution

**Status: INFRASTRUCTURE EXISTS / LIVE DISABLED**

VelocityAtlas remains independent from SignalAtlas.

SignalAtlas can eventually emit:

**intent**

VelocityAtlas controls:

**execution permission**

No AI agent, frontend or SignalAtlas model can bypass Velocity risk controls.

Before any funded deployment:

- credentials rotated
- signer/security path audited
- order-book execution path audited
- fail-open risks eliminated
- exchange-truth reconciliation validated
- kill switches tested
- hard capital limits tested
- tiny-notional canary deployment
- rollback tested

Progression:

**shadow → paper → dry-run → tiny live → bounded live → controlled scaling**

Never:

**research model → unrestricted live capital**

---

## Phase 8 — Strategy Vault & Capital Scaling

**Status: FUTURE**

Only proven live strategies qualify.

Capabilities may include:

- strategy vaults
- capital allocation
- risk budgeting
- performance attribution
- capacity estimation
- strategy retirement
- investor/fund structures
- performance-fee models

Scaling is evidence driven.

Capital increases only when:

- live economics remain consistent
- execution capacity supports it
- drawdowns remain inside envelope
- monitoring and recovery are mature

---

## Phase 9 — Agent Intelligence & Autonomous Market Infrastructure

**Status: LONG-TERM**

This becomes the mature form of the original Agent Intelligence Layer.

SignalAtlas becomes an intelligence substrate used by humans and autonomous systems.

Agents can:

- discover markets
- query market state
- query event structure
- inspect resolution state
- compare related markets
- consume certified intelligence
- request execution intents
- inspect performance
- perform research workflows

Agents cannot:

- redefine truth
- override model certification
- bypass risk limits
- bypass VelocityAtlas
- alter immutable resolution history
- manufacture missing data

Long-term architecture:

**SignalAtlas = intelligence authority**

**VelocityAtlas = permissioned execution authority**

**EdgeAtlas = human operator interface**

**SDK/MCP/API = machine interface**

---

## Cross-Phase Certification Model

From now on, major components should move through explicit lifecycle states:

**EXPERIMENTAL → MEASURED → VALIDATED → CERTIFIED → FROZEN**

A frozen component changes only through a new versioned workstream with evidence explaining why.

Examples already following this model:

- Resolution Truth v1 — CERTIFIED / FROZEN
- API v2.1.0 — CERTIFIED / FROZEN
- Execution Economics — COMPLETE / FROZEN
- Data Durability & DR v1 — CERTIFIED / FROZEN
- Source Control & Release Integrity v1 — CERTIFIED / FROZEN

This should become permanent SignalAtlas governance.

---

## Current Position — 26 September 2026

### Foundation

**~90–95% complete**

Strongest areas:

- canonical measurement
- CLOB truth
- forward outcomes
- resolution truth
- deterministic API
- EdgeAtlas infrastructure
- backup / DR
- source integrity
- architecture boundaries

### Intelligence

**Research stage**

No production directional alpha is currently certified.

### Brain

**FAIL-CLOSED**

Correct state.

### Execution

SignalAtlas:

**NONE**

VelocityAtlas:

**isolated / live disabled**

### Product

EdgeAtlas:

**operator platform shell available**

Certified intelligence surfaces:

**pending**

### Commercialization

**not yet activated**

### Immediate next dependency

**Clean-VPS Rebuild Rehearsal v1**

Then:

**Sep-29 Event Measurement checkpoint**

Then:

**Universe Architecture + Phase-1 intelligence research**

---

## Near-Term Execution Order

For the coming work, lock the sequence as:

1. Clean-VPS Rebuild Rehearsal v1
2. Event Measurement 72h analysis
3. Decide event-measurement continuation / schema stability
4. Canonical Universe Index + CLOB verification architecture
5. Begin Phase-1 prospective intelligence research
6. Certify or reject candidate signal families individually
7. Only then open Brain shadow decisions
8. Activate corresponding EdgeAtlas intelligence surfaces
9. Expose certified intelligence through API/SDK/MCP
10. Only after paper/shadow validation consider VelocityAtlas execution

That sequence is now the shortest route to a serious product because it avoids rebuilding layers later.

---

## What Changes Relative to the Old Roadmap

The old roadmap went roughly:

**Intelligence → Terminal → Audience → Revenue → API → Platform → Vault → Agents**

The canonical roadmap is now:

**Truth/Foundation → Calibrated Intelligence → Brain Certification → Portfolio Validation → Operator Intelligence → API/Agent Distribution → Commercial Intelligence → Permissioned Execution → Strategy Scaling → Autonomous Agent Infrastructure**

This v2.0 document is the canonical roadmap. The pre-v2 roadmap remains only in Git history and must not coexist as a competing source of architectural truth.
