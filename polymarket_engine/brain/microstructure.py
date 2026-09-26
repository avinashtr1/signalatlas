class MicrostructureAnalyzer:
    """
    Truth-preserving microstructure diagnostics.

    No alpha score is produced until these features are calibrated against
    forward outcomes and real CLOB depth/execution data.
    """

    def analyze(self, candidate, cache_features: dict):
        snap = candidate.market_state.liquidity_snapshot or {}

        return {
            # Fail closed: diagnostics are not probability edge.
            "microstructure_score": 0.0,
            "microstructure_reasons": ["microstructure_unscored"],

            "quote_state": snap.get("quote_state"),
            "two_sided": bool(snap.get("two_sided", False)),
            "best_bid": snap.get("best_bid"),
            "best_ask": snap.get("best_ask"),
            "mid_price": snap.get("mid_price"),
            "spread": snap.get("spread"),

            "liquidity_usd": snap.get("liquidity_usd"),
            "volume_total_usd": snap.get("volume_total_usd"),

            "reference_price_change": cache_features.get(
                "reference_price_change"
            ),
            "mid_price_change": cache_features.get("mid_price_change"),
            "liquidity_change": cache_features.get("liquidity_change"),
            "volume_change": cache_features.get("volume_change"),
            "spread_change": cache_features.get("spread_change"),
            "observation_interval_seconds": cache_features.get(
                "observation_interval_seconds"
            ),

            # Not known from Gamma metadata.
            "quote_age_seconds": None,
            "staleness_seconds": None,

            # Not known until CLOB depth measurement is added.
            "depth_bps": None,

            # Backward compatibility.
            "price_velocity": cache_features.get(
                "reference_price_change"
            ),
            "volume_usd": snap.get("volume_total_usd"),
        }
