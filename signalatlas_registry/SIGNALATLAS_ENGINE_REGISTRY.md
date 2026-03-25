# SignalAtlas Engine Registry

Purpose:
Document all intelligence engines powering SignalAtlas.

This file acts as the canonical registry for system modules.

---

1. Universe Scanner
Purpose:
Collect raw markets from prediction platforms.

Input:
External market APIs

Output:
Raw market universe

Used by:
Universe Cleaner

---

2. Universe Cleaner
Purpose:
Remove spam, duplicates, and invalid markets.

Input:
Raw universe

Output:
Clean universe

Used by:
Mispricing Engine
Cluster Engine

---

3. Mispricing Engine
Purpose:
Detect probability deviations between market price and model probability.

Input:
Clean markets

Output:
Mispricing signals

Used by:
Alpha Feed
Allocator

---

4. Liquidity Vacuum Engine
Purpose:
Detect situations where liquidity gaps allow fast repricing.

Input:
Orderbook data

Output:
Vacuum signals

Used by:
Alpha Feed

---

5. Microstructure Engine
Purpose:
Analyze order flow, spread widening, and depth imbalance.

Input:
Orderbook snapshots

Output:
Microstructure score

Used by:
Executive Intelligence

---

6. Resolution Arbitrage Engine
Purpose:
Detect markets close to resolution with stale pricing.

Input:
Market metadata
External data feeds

Output:
Resolution arbitrage signals

Used by:
Alpha Feed

---

7. Narrative Cluster Engine
Purpose:
Group markets into narratives.

Example:
NBA Champion
US Election
AI Regulation

Input:
Clean market universe

Output:
Narrative clusters

Used by:
Heatmap
Radar
Terminal

---

8. Allocator Engine
Purpose:
Determine capital allocation per signal.

Input:
Signal edge
Liquidity
Risk model

Output:
Allocated capital per trade

Used by:
Execution layer

---

9. Executive Intelligence Engine
Purpose:
Generate executive summary of system state.

Input:
All engines

Output:
/api/executive

Used by:
Terminal
Dashboard
Telegram Alpha Feed

---

10. Signal Memory Engine (planned)
Purpose:
Track lifecycle of signals.

Tracks:
signal generated
signal deployed
signal resolved
PnL
edge accuracy

Used by:
model calibration
performance analytics

---

