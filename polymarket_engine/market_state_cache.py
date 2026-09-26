from datetime import datetime, timezone


class MarketStateCache:
    """
    Stores consecutive observed market snapshots.

    Important semantics:
    - observation_interval_seconds is OUR sampling interval.
    - it is NOT quote staleness.
    - liquidity_change uses reported liquidity, not volume.
    - missing observations remain None rather than becoming synthetic zeroes.
    """

    def __init__(self):
        self._cache = {}

    def _snapshot(self, market_state):
        snap = market_state.liquidity_snapshot or {}

        return {
            "reference_price": market_state.current_price,
            "mid_price": snap.get("mid_price"),
            "best_bid": snap.get("best_bid"),
            "best_ask": snap.get("best_ask"),
            "spread": snap.get("spread"),
            "liquidity_usd": snap.get("liquidity_usd"),
            "volume_total_usd": snap.get("volume_total_usd"),
            "quote_state": snap.get("quote_state"),
            "observed_at": snap.get("observed_at"),
            "internal_observed_at": datetime.now(timezone.utc),
        }

    def update(self, market_state):
        market_id = market_state.market_id
        prev = self._cache.get(market_id)
        current = self._snapshot(market_state)
        self._cache[market_id] = current
        return prev, current

    def get(self, market_id):
        return self._cache.get(market_id)

    @staticmethod
    def _delta(current, previous):
        if current is None or previous is None:
            return None
        try:
            return float(current) - float(previous)
        except Exception:
            return None

    def compute_features(self, market_state):
        prev = self.get(market_state.market_id)

        if prev is None:
            _, current = self.update(market_state)

            return {
                "reference_price_change": None,
                "mid_price_change": None,
                "liquidity_change": None,
                "volume_change": None,
                "spread_change": None,
                "observation_interval_seconds": None,

                # Backward-compatible field name, now correctly nullable.
                "price_velocity": None,

                # Deliberately unavailable: Gamma updatedAt is not proven
                # to be top-of-book quote freshness.
                "quote_age_seconds": None,
                "staleness_seconds": None,
            }

        _, current = self.update(market_state)

        interval = (
            current["internal_observed_at"]
            - prev["internal_observed_at"]
        ).total_seconds()

        reference_change = self._delta(
            current["reference_price"],
            prev["reference_price"],
        )

        return {
            "reference_price_change": reference_change,
            "mid_price_change": self._delta(
                current["mid_price"],
                prev["mid_price"],
            ),
            "liquidity_change": self._delta(
                current["liquidity_usd"],
                prev["liquidity_usd"],
            ),
            "volume_change": self._delta(
                current["volume_total_usd"],
                prev["volume_total_usd"],
            ),
            "spread_change": self._delta(
                current["spread"],
                prev["spread"],
            ),
            "observation_interval_seconds": interval,

            # Compatibility only.
            "price_velocity": reference_change,

            "quote_age_seconds": None,
            "staleness_seconds": None,
        }
