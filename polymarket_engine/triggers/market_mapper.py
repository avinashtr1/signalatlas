from datetime import datetime, timezone
from ..models.trigger_event import TriggerEvent
from ..models.candidate_opportunity import CandidateOpportunity
from ..models.market_state import MarketState
from ..data_adapters.polymarket_adapter import PolymarketAdapter
from ..config.market_filters import MarketFilterConfig


class MarketMapper:
    def __init__(self, config: MarketFilterConfig):
        self.config = config
        self.polymarket_adapter = PolymarketAdapter()

    def _apply_selection_rules(self, market_state, trigger_event):
        return True, "selected_by_rule"

    def _determine_strategy_type(self, trigger_event, market_state):
        return "TEST_STRATEGY"

    def _parse_iso_datetime(self, date_string: str):
        if date_string.endswith('Z'):
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return datetime.fromisoformat(date_string)

    def _compute_market_specific_signal_strength(self, trigger_event, market_state):
        base_signal = abs(
            trigger_event.details.get("change")
            or trigger_event.details.get("std_dev")
            or 0.0
        )

        price = market_state.current_price
        volume = (market_state.liquidity_snapshot or {}).get("volume_usd", 0.0)

        mid_factor = max(0.25, 1.0 - abs(price - 0.5) * 1.5)
        volume_factor = min(1.5, max(0.5, (max(volume, 1.0) / 150000.0) ** 0.20))

        now = trigger_event.trigger_timestamp
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        days_to_resolution = max(
            1.0,
            (market_state.end_time - now).total_seconds() / 86400.0
        )

        time_factor = min(1.5, max(0.5, (30.0 / days_to_resolution) ** 0.25))

        return base_signal * mid_factor * volume_factor * time_factor

    def map_trigger_to_candidates(self, trigger_event: TriggerEvent):
        candidate_opportunities = []

        all_markets = self.polymarket_adapter.get_markets_for_trigger(trigger_event)

        for market_data in all_markets:
            try:
                market_state = MarketState(
                    market_id=market_data['market_id'],
                    name=market_data['name'],
                    end_time=self._parse_iso_datetime(market_data['end_time']),
                    current_price=market_data['current_price'],
                    liquidity_snapshot=market_data.get('liquidity_snapshot'),
                    truth_source=market_data.get('truth_source'),
                    truth_source_confidence=market_data.get('truth_source_confidence'),
                    objective_support=market_data.get('objective_support', False),
                    market_type=market_data.get('market_type', 'unknown'),
                    event_group=market_data.get('event_group')
                )

                is_relevant, reason = self._apply_selection_rules(market_state, trigger_event)

                if is_relevant:
                    market_signal = self._compute_market_specific_signal_strength(trigger_event, market_state)

                    candidate_opportunities.append(
                        CandidateOpportunity(
                            trigger_type=trigger_event.trigger_type,
                            source_venue=trigger_event.source_venue,
                            source_symbol=trigger_event.source_symbol,
                            trigger_timestamp=trigger_event.trigger_timestamp,
                            market_state=market_state,
                            strategy_type=self._determine_strategy_type(trigger_event, market_state),
                            selector_reason=reason,
                            signal_strength=market_signal,
                            signal_details={
                                **trigger_event.details,
                                "market_specific_signal_strength": market_signal,
                                "market_price": market_state.current_price,
                                "market_volume_usd": (market_state.liquidity_snapshot or {}).get("volume_usd", 0.0),
                                "relation_type": market_data.get("relation_type"),
                                "bucket_group_id": market_data.get("bucket_group_id"),
                                "bucket_group_title": market_data.get("bucket_group_title"),
                                "bucket_group_prices": market_data.get("bucket_group_prices", []),
                                "group_item_title": market_data.get("group_item_title"),
                            },
                            market_selection_priority="high",
                            liquidity_quality="HIGH",
                            risk_flags=[]
                        )
                    )

            except Exception as e:
                print(f"ERROR: {e}")

        return candidate_opportunities
