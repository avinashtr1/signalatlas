# SignalAtlas Canonical Architecture

Vision:
SignalAtlas = Intelligence platform for prediction markets

Design Principle:
Engines compute  
APIs expose  
UIs display  
Telegram distributes

Business logic MUST never live in dashboards, feeds, or UI code.

---

# Canonical Objects

These are the core objects the entire platform must use.

## CanonicalMarket

Normalized representation of any prediction market.

Fields:

venue
market_id
market_name
outcomes
liquidity
volume_24h
resolution_time
category
status

Example venues:

Polymarket
Kalshi
Manifold
PredictIt

---

## CanonicalSignal

Represents an opportunity detected by intelligence engines.

Fields:

signal_id
market_id
side
entry_price
structural_edge
microstructure_score
vacuum_score
expected_net_edge_pct
expected_fill_probability
timestamp

---

## CanonicalTrade

Represents an executed position.

Fields:

trade_id
signal_id
venue
side
entry_price
size
capital_allocated
status
pnl
timestamp

---

## CanonicalRegime

Represents macro market conditions.

Fields:

regime_type
volatility_state
liquidity_state
sentiment_state
timestamp

---

## CanonicalSnapshot

Unified state of the intelligence system.

Fields:

signals_detected
signals_executed
signals_resolved
top_opportunity
recommendations
system_status
allocated_capital
timestamp

---

# Venue Adapter Layer

Adapters normalize venue data into CanonicalMarket.

Examples:

PolymarketAdapter
KalshiAdapter
ManifoldAdapter
PredictItAdapter

Adapters may:

collect data  
normalize structures  
handle venue quirks

Adapters MUST NOT contain trading logic.

---

# Intelligence Layer

Engines operate only on canonical objects.

Examples:

Mispricing Engine  
Liquidity Vacuum Engine  
Resolution Arbitrage Engine  
Microstructure Engine  
Market Regime Engine

Engines output CanonicalSignal objects.

---

# Orchestration Layer

Allocator decides capital distribution.

Components:

Signal Ranking  
Capital Allocation  
Deployable Opportunities

---

# Execution Layer

Executes trades via venue adapters.

Examples:

Polymarket Execution  
Kalshi Execution

Execution layer consumes CanonicalTrade.

---

# Interface Layer

Interfaces must only display data.

Allowed:

Terminal  
Ops Dashboard  
Brain Monitor  
Telegram Feed

Forbidden:

Embedding intelligence logic in UI.

---

# Anti-Patterns (Strictly Forbidden)

Business logic inside UI  
Exchange-specific signals  
Engines reading raw venue data  
Hardcoding venue logic inside intelligence engines

---

# Long-Term Platform Goal

SignalAtlas =

70% Bloomberg Terminal  
30% Nansen Analytics

for prediction markets.

