from datetime import datetime, timezone, timedelta
import collections

# Import models and adapters from the polymarket_engine package
from ..models.trigger_event import TriggerEvent
from ..data_adapters.binance_adapter import BinanceAdapter
from ..data_adapters.hyperliquid_adapter import HyperliquidAdapter
from ..data_adapters.polymarket_adapter import PolymarketAdapter

# --- Trigger Thresholds (would be loaded from config) ---
MOMENTUM_BURST_THRESHOLD_USD = 500.0
VOLATILITY_SPIKE_THRESHOLD_STDDEV = 300.0
TIME_TO_RESOLUTION_SHORT_HOURS = 48.0
TIME_TO_RESOLUTION_CRITICAL_HOURS = 12.0

class SignalListener:
    """
    Listens to data streams from adapters, detects explicit trigger
    conditions, and emits standardized TriggerEvent objects.
    """
    def __init__(self):
        self.binance_adapter = BinanceAdapter()
        self.hyperliquid_adapter = HyperliquidAdapter()
        self.polymarket_adapter = PolymarketAdapter()

        # State for price-based signal detection
        self.last_binance_btc_price: float | None = None
        self.last_hl_btc_price: float | None = None
        self.price_history: dict[str, collections.deque] = {
            "BTC/USDT": collections.deque(maxlen=20),
            "BTC/USDC": collections.deque(maxlen=20)
        }

    def _check_price_signals(self, now: datetime) -> list[TriggerEvent]:
        """Checks for price-based triggers from exchange adapters."""
        events = []

        # 1. Binance BTC Price Check
        try:
            binance_data = self.binance_adapter.get_btc_price()
            current_price = binance_data["price"]
            symbol = binance_data["symbol"]
            self.price_history[symbol].append(current_price)

            # Check for Momentum Burst
            if self.last_binance_btc_price is not None:
                price_change = current_price - self.last_binance_btc_price
                if abs(price_change) > MOMENTUM_BURST_THRESHOLD_USD:
                    events.append(TriggerEvent(
                        trigger_type="price_momentum_burst",
                        source_venue="Binance",
                        source_symbol="BTC",
                        trigger_timestamp=now,
                        details={"price": current_price, "change": price_change}
                    ))

            # Check for Volatility Spike
            if len(self.price_history[symbol]) >= 10: # Require min data points
                prices = list(self.price_history[symbol])
                mean = sum(prices) / len(prices)
                std_dev = (sum([(p - mean) ** 2 for p in prices]) / len(prices)) ** 0.5
                if std_dev > VOLATILITY_SPIKE_THRESHOLD_STDDEV:
                    events.append(TriggerEvent(
                        trigger_type="volatility_spike",
                        source_venue="Binance",
                        source_symbol="BTC",
                        trigger_timestamp=now,
                        details={"price": current_price, "std_dev": std_dev}
                    ))

            self.last_binance_btc_price = current_price
        except Exception as e:
            print(f"SignalListener ERROR fetching from Binance: {e}")

        # 2. Hyperliquid BTC Price Check (similar logic)
        # ... (implementation would mirror Binance logic for Hyperliquid)

        return events

    def _check_time_and_resolution_signals(self, now: datetime) -> list[TriggerEvent]:
        """
        Polls the Polymarket adapter to check for time-based and
        resolution-based triggers across all relevant markets.
        """
        events = []
        # Create a dummy trigger to fetch all relevant markets for polling
        polling_trigger = TriggerEvent("polling", "system", "all", now)
        all_markets = self.polymarket_adapter.get_markets_for_trigger(polling_trigger)

        for market in all_markets:
            try:
                end_time = datetime.fromisoformat(market["end_time"].replace('Z', '+00:00'))
                time_to_res_sec = (end_time - now).total_seconds()
                
                if time_to_res_sec <= 0:
                    continue # Market has resolved

                time_to_res_hours = time_to_res_sec / 3600

                # Check for Critical Time to Resolution
                if time_to_res_hours <= TIME_TO_RESOLUTION_CRITICAL_HOURS:
                    events.append(TriggerEvent(
                        trigger_type="time_to_resolution_critical",
                        source_venue="Polymarket",
                        source_symbol=market["market_id"],
                        trigger_timestamp=now,
                        details={"time_to_resolution_hours": time_to_res_hours}
                    ))
                # Check for Short Time to Resolution
                elif time_to_res_hours <= TIME_TO_RESOLUTION_SHORT_HOURS:
                    events.append(TriggerEvent(
                        trigger_type="time_to_resolution_short",
                        source_venue="Polymarket",
                        source_symbol=market["market_id"],
                        trigger_timestamp=now,
                        details={"time_to_resolution_hours": time_to_res_hours}
                    ))
                
                # Check for Resolution Condition Met (Simulation)
                # In a real system, this would require a dedicated service to watch for
                # event outcomes (e.g., news API for an FOMC announcement).
                if market["market_type"] == "event" and time_to_res_hours < 1.0:
                    # Simulate that for event markets resolving in <1hr, we might
                    # have an external confirmation.
                    events.append(TriggerEvent(
                        trigger_type="resolution_condition_met",
                        source_venue="TruthSource", # Indicates the source is external confirmation
                        source_symbol=market["truth_source"],
                        trigger_timestamp=now,
                        details={"market_id": market["market_id"], "market_name": market["name"]}
                    ))

            except Exception as e:
                print(f"SignalListener ERROR processing market {market.get('market_id')}: {e}")

        # Deduplicate events (e.g., time triggers might fire repeatedly)
        unique_events = {f'{e.trigger_type}-{e.source_symbol}': e for e in events}
        return list(unique_events.values())

    def listen_for_signals(self) -> list[TriggerEvent]:
        """
        Main entry point. Runs all checks and returns a consolidated
        list of detected trigger events.
        """
        now = datetime.now(timezone.utc)
        
        price_events = self._check_price_signals(now)
        time_res_events = self._check_time_and_resolution_signals(now)
        
        # periodic market scan trigger
        system_scan = TriggerEvent("market_scan", "system", "BTC", now)
        scan_events = [system_scan]
        return price_events + time_res_events + scan_events
