from datetime import datetime, timezone


class MarketStateCache:
    """
    Stores last known market states so we can detect
    price changes, staleness, liquidity collapse, etc.
    """

    def __init__(self):
        self._cache = {}

    def update(self, market_state):
        market_id = market_state.market_id

        now = datetime.now(timezone.utc)

        prev = self._cache.get(market_id)

        snapshot = {
            "price": market_state.current_price,
            "volume": (market_state.liquidity_snapshot or {}).get("volume_usd", 0),
            "timestamp": now,
        }

        self._cache[market_id] = snapshot

        return prev, snapshot

    def get(self, market_id):
        return self._cache.get(market_id)

    def compute_features(self, market_state):
        """
        Returns microstructure signals:
        - price_velocity
        - liquidity_change
        - staleness_seconds
        """

        prev = self.get(market_state.market_id)

        if not prev:
            self.update(market_state)
            return {
                "price_velocity": 0.0,
                "liquidity_change": 0.0,
                "staleness_seconds": 0.0,
            }

        now = datetime.now(timezone.utc)

        price = market_state.current_price
        volume = (market_state.liquidity_snapshot or {}).get("volume_usd", 0)

        price_velocity = price - prev["price"]
        liquidity_change = volume - prev["volume"]

        staleness_seconds = (now - prev["timestamp"]).total_seconds()

        self.update(market_state)

        return {
            "price_velocity": price_velocity,
            "liquidity_change": liquidity_change,
            "staleness_seconds": staleness_seconds,
        }
