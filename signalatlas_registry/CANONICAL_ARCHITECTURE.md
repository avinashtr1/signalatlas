# SignalAtlas Canonical Architecture

## Vision

SignalAtlas is prediction-market intelligence infrastructure for humans and AI agents.

VelocityAtlas is the permissioned execution layer.

Long-term product direction:

70% Bloomberg Terminal
+
30% Nansen Analytics

for prediction markets.

---

# Design Principles

Data establishes truth.

Measurements preserve observations.

Intelligence must be calibrated from evidence.

Brain decisions must fail closed when evidence is insufficient.

Execution is downstream of risk controls.

APIs expose canonical state.

UIs display state.

Distribution surfaces do not contain business logic.

---

# Current Canonical Data Objects

The canonical schemas currently exist in JSON / SQLite records.

They are not yet required to exist as formal Python dataclasses.

Avoid creating duplicate object systems unless there is a concrete need.

---

## CanonicalMarket / Snapshot Measurement

Current implementation:

snapshots table in

analytics/market_measurements.sqlite3

Core fields include:

market_id
event_id
market_name
event_title
observed_at
observation_bucket
source_updated_at
source
reference_price
best_bid
best_ask
mid_price
spread
quote_state
two_sided
tradable_top_of_book
active
closed
archived
accepting_orders
volume_total_usd
liquidity_usd
yes_token_id
no_token_id
structural_group_type
neg_risk
neg_risk_augmented
neg_risk_market_id
bucket_group_id
raw_resolution_time
resolution_time_valid
schema_version

Important semantics:

source_updated_at is source metadata, not quote age.

resolution_time_valid must be true before resolution timing can be used.

0 / 1 pseudo-quotes are not valid executable books.

---

## CLOB Measurement

Current implementation:

clob_books table

Real CLOB books are authoritative for execution-quality measurement.

Stored metrics include:

best bid / ask
spread
level counts
top sizes
total bid / ask shares
total bid / ask notional
1c / 2c / 5c depth
$10 / $50 / $100 buy VWAP and fill
$10 / $50 / $100 sell VWAP and fill

No synthetic depth is permitted.

### Economic execution truth

Gross price movement is not equivalent to executable economic edge.

Canonical execution-quality research must use the same position quantity on entry and exit.

A round trip is considered exactly reconstructible only when the measured book contains sufficient observed depth to execute the required share quantity on both legs.

Applicable taker costs must use the actual per-market fee configuration observed for that market. Fee-free markets remain fee-free. Research must not infer fee rates from category labels when market-specific metadata is available.

The canonical baseline assumes zero taker rebate. Account-specific or volume-tier rebates may be evaluated separately as sensitivity scenarios but must not be embedded into baseline alpha.

Spread and book slippage are represented through observed executable prices and depth. They must not be added again as synthetic costs when already captured by execution prices.

Fixed-dollar $10 / $50 / $100 VWAP comparisons remain useful execution diagnostics, but entry and exit VWAP at equal dollar notional do not necessarily represent the same share quantity.

Historical exact same-share reconstruction is currently possible when the intended position fits entirely within observed top-of-book size at both entry and exit. Observations requiring deeper same-share execution must not be treated as exactly reconstructed unless sufficient level data is available.

The canonical economic research outcome is:

net executable PnL = same-share executable gross PnL - applicable execution fees and other measured unavoidable costs

A positive gross gap alone is not an economic success condition.

Net executable PnL greater than zero is an economic measurement outcome only. It does not by itself constitute alpha, calibration, Brain eligibility, or permission to execute.

---

## Forward Outcome

Current implementation:

forward_outcomes table

Horizons:

1 hour
6 hours
24 hours

Labels are based on actual future observations.

Possible states include observed future quote states and missing-in-collected-scope.

Pending horizons remain unlabeled until mature.

No fabricated validation result is permitted.

---

## Resolution Truth

Status:

CERTIFIED / FROZEN V1

Canonical implementation:

resolution_collector.py

Canonical tables:

resolution_watch
market_resolutions

Resolution identity is mapped from previously observed SignalAtlas market IDs to Polymarket Gamma condition IDs and outcome ordering.

Gamma is identity and metadata infrastructure for this layer. Gamma closed state, active state, outcomePrices, and endDate are not authoritative settlement truth.

Polygon Conditional Tokens Framework is the canonical settlement authority.

Contract:

0x4D97DCd97eC945f40cF65F87097ACe5EA0476045

Chain:

Polygon mainnet / chain ID 137

A condition is considered resolved only when its on-chain payoutDenominator is non-zero and its payout vector passes consistency validation.

Canonical resolution records preserve the raw payout denominator, raw payout numerators, normalized payout vector, and mapped outcome labels.

raw_resolution_time / Gamma endDate may be used only as a polling-scheduling hint. It must never be treated as actual resolution time.

Every READY condition receives a prospective Polygon block anchor while unresolved.

When a previously anchored condition transitions to resolved, SignalAtlas searches the bounded block interval for the matching ConditionResolution event.

resolution_time_valid may become true only when the corresponding ConditionResolution event is recovered and its Polygon block timestamp is recorded.

Until such event evidence exists, first_observed_resolved_at is observation metadata only and must not be presented as the authoritative resolution timestamp.

Resolved payout records are immutable. A conflicting payout vector is a hard integrity failure.

Legacy auto-settlement, price-based winner inference, manually populated market outcomes, and execution-layer resolution watchers are not canonical resolution truth.

Resolution Truth does not enable Resolution Arbitrage by itself. Brain remains fail-closed until a separately calibrated resolution-arbitrage model exists.

---

# Venue Adapter Layer

Current canonical adapter:

PolymarketAdapter

Responsibilities:

collect venue data
normalize venue structures
sanitize quote semantics
preserve source metadata
preserve structural-market metadata

Adapters must not contain trading decisions.

---

# Structural Market Semantics

NegRisk markets are classified as:

STANDARD_NEGRISK
AUGMENTED_NEGRISK
STANDALONE

Only standard non-augmented NegRisk groups are currently eligible for structural basket analysis.

Structural group edge must never be assigned directly to individual child markets.

Basket execution is not currently implemented.

---

# Intelligence Layer

Current state:

FROZEN / UNSCORED where evidence is insufficient.

Microstructure:

measurement only
score = 0
unscored

Liquidity vacuum:

disabled pending real-depth calibration

Resolution arbitrage:

fail-closed when resolution time is unverified

Directional alpha:

not currently calibrated

No intelligence engine may manufacture edge from heuristics and present it as validated alpha.

---

# Brain Layer

Current Brain behavior is fail-closed.

Standalone markets:

reject — no calibrated directional alpha model

Structural group members:

reject — basket execution required

No deployable signal should currently emerge from the Brain.

---

# Execution Layer

SignalAtlas does not currently execute trades through its canonical API.

VelocityAtlas remains the separate execution system.

Execution must consume permissioned intents and must not allow an API or agent to bypass risk controls.

---

# API Layer

Canonical API:

polymarket_engine/api_server.py

Service:

signalatlas-measurement-api.service

Bind:

127.0.0.1:8011

Mode:

read-only

Current API version:

2.1.0

Current API exposes:

measurement health
API authority / freshness metadata
latest markets
latest market snapshot
CLOB measurements
snapshot history
forward outcomes
resolution watch / chain-check status
immutable CTF settlement records
resolution event evidence when available

Measurement endpoints operate on the current partial active-event slice.

Resolution endpoints operate on historically observed SignalAtlas markets tracked by resolution_watch.

Neither scope may be represented as complete Polymarket universe coverage.

event_measurements remains frozen as a prospective experiment and is not exposed through the API.

No calibrated signal endpoint currently exists.

Legacy intelligence API:

retired / fail-closed

---

# Agent Architecture

Long-term API path:

read-only intelligence
→ sandbox / paper intents
→ constrained live execution

Agents may submit intents.

Agents must never bypass:

risk limits
position limits
execution validation
permissions
idempotency
audit logging

REST / OpenAPI is canonical.

Python SDK and MCP/tool surfaces may be layered later.

---

# Anti-Patterns

Forbidden:

business logic in dashboards

business logic in Telegram

synthetic liquidity presented as real liquidity

synthetic fills presented as executable fills

unverified resolution timestamps used as truth

group structural edge assigned to single children

stale analytics exposed as current intelligence

API endpoints executing arbitrary shell pipelines

agent access bypassing execution controls

parallel duplicate modules when a canonical module exists

---

# Current Canonical Flow

Gamma + CLOB
→ canonical measurements
→ durable SQLite history
→ forward outcomes
→ measurement health
→ canonical on-chain resolution truth
→ read-only OpenAPI

Next intelligence work begins only after sufficient measured history exists.
