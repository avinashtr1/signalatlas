from datetime import datetime

class MarketState:
    """Holds fetched market context and static properties."""
    def __init__(self,
                 market_id: str,
                 name: str,
                 end_time: datetime,
                 current_price: float,
                 liquidity_snapshot: dict | None = None,
                 truth_source: str | None = None,
                 truth_source_confidence: float | None = None,
                 objective_support: bool = False,
                 market_type: str = "unknown",
                 event_group: str | None = None):
        self.market_id = market_id
        self.name = name
        self.end_time = end_time
        self.current_price = current_price
        self.liquidity_snapshot = liquidity_snapshot if liquidity_snapshot else {}
        self.truth_source = truth_source
        self.truth_source_confidence = truth_source_confidence
        self.objective_support = objective_support
        self.market_type = market_type
        self.event_group = event_group
