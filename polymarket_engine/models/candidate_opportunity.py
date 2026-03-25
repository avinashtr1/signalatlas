import uuid
from datetime import datetime
from .market_state import MarketState

class CandidateOpportunity:
    def __init__(self,
                 trigger_type: str, source_venue: str, source_symbol: str,
                 trigger_timestamp: datetime, market_state: MarketState,
                 strategy_type: str, selector_reason: str,
                 signal_strength: float | None, signal_details: dict,
                 market_selection_priority: str | None,
                 liquidity_quality: str | None, risk_flags: list[str],
                 fair_probability_estimate: float | None = None,
                 raw_edge: float | None = None,
                 expected_net_edge: float | None = None,
                 annualized_edge: float | None = None):
        self.candidate_version: str = "1.0"
        self.candidate_id: str = str(uuid.uuid4())
        self.trigger_type, self.source_venue, self.source_symbol = trigger_type, source_venue, source_symbol
        self.trigger_timestamp, self.market_state = trigger_timestamp, market_state
        self.strategy_type, self.selector_reason = strategy_type, selector_reason
        self.signal_strength, self.signal_details = signal_strength, signal_details
        self.market_selection_priority, self.liquidity_quality, self.risk_flags = market_selection_priority, liquidity_quality, risk_flags
        self.truth_source, self.truth_source_confidence = market_state.truth_source, market_state.truth_source_confidence
        self.objective_resolution_supported = market_state.objective_support
        self.days_to_resolution = max(0, (market_state.end_time - trigger_timestamp).total_seconds() / 86400)
        self.dedupe_key = f"{market_state.market_id}_{strategy_type}"
        self.fair_probability_estimate, self.raw_edge = fair_probability_estimate, raw_edge
        self.expected_net_edge, self.annualized_edge = expected_net_edge, annualized_edge
