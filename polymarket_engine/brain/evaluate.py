from polymarket_engine.market_state_cache import MarketStateCache
from .liquidity_vacuum import LiquidityVacuumDetector
from .microstructure import MicrostructureAnalyzer
from .resolution_arb import ResolutionArbDetector
from ..models.candidate_opportunity import CandidateOpportunity
from ..config.market_filters import MarketFilterConfig
from polymarket_engine.brain.gates import Gates
from polymarket_engine.brain.inventory import Inventory


T_MIN_SIGNAL_STRENGTH = 380
T_MIN_STRUCTURAL_EDGE = 0.06
T_MIN_RAW_STRUCTURAL_EDGE = 0.03

T_MIN_BUCKET_SUM = 0.97
T_MAX_BUCKET_SUM = 1.12
T_MIN_BUCKET_COUNT = 2
T_MAX_BUCKET_COUNT = 16
T_MIN_PRICE = 0.03
T_MAX_PRICE = 0.97


class BrainEvaluator:
    def __init__(self, config: MarketFilterConfig, gates_instance: Gates, inventory_instance: Inventory):
        self.config = config
        self.gates = gates_instance
        self.inventory = inventory_instance
        self.vacuum_detector = LiquidityVacuumDetector()
        self.market_cache = MarketStateCache()
        self.microstructure = MicrostructureAnalyzer()
        self.resolution_arb = ResolutionArbDetector()

    def _structural_signal(self, candidate: CandidateOpportunity):
        """
        Structural NegRisk edge is a basket-level property.

        The current CandidateOpportunity / PaperExecutor path executes one
        child market at a time, so it cannot safely execute a multi-leg
        NegRisk basket.

        Fail closed until a canonical group-level candidate and basket
        execution path exist.
        """
        details = candidate.signal_details or {}
        relation_type = details.get("relation_type")

        if relation_type == "bucket_member":
            return (
                0.0,
                "NONE",
                "structural_group_requires_basket_execution",
            )

        return 0.0, "NONE", "no_structural_group"

    def evaluate_candidate(self, candidate: CandidateOpportunity):
        """
        Truth-only evaluator.

        Current policy:
        - NegRisk structural opportunities require group/basket execution.
        - No calibrated standalone directional-alpha model exists yet.
        - Microstructure/vacuum/resolution are diagnostics only.
        - No synthetic fill probability, slippage, fee, rank score, or
          expected net edge is manufactured.
        """

        if candidate.signal_strength is None:
            return {
                "decision": "REJECT",
                "reason": "missing_signal",
                "analysis": {},
                "candidate": candidate,
            }

        cache_features = self.market_cache.compute_features(
            candidate.market_state
        )

        micro = self.microstructure.analyze(
            candidate,
            cache_features,
        )

        vacuum_score, vacuum_signal, vacuum_reason = (
            self.vacuum_detector.detect(
                candidate,
                cache_features,
            )
        )

        resolution_score, resolution_signal, resolution_reason = (
            self.resolution_arb.detect(candidate)
        )

        structural_edge, trade_side, structural_reason = (
            self._structural_signal(candidate)
        )

        details = candidate.signal_details or {}
        relation_type = details.get("relation_type")

        # No probability/executable edge exists on this single-market path.
        candidate.raw_edge = None
        candidate.expected_net_edge = None
        candidate.annualized_edge = None

        analysis = {
            "trade_side": None,
            "structural_edge": structural_edge,

            # Explicitly unavailable until calibrated.
            "total_edge": None,
            "raw_edge": None,
            "expected_fill_probability": None,
            "expected_slippage": None,
            "fee_cost": None,
            "expected_net_edge_pct": None,
            "annualized_edge_pct": None,
            "rank_score": None,

            # Diagnostics only.
            "vacuum_score": vacuum_score,
            "vacuum_signal": vacuum_signal,
            "vacuum_reason": vacuum_reason,

            "resolution_score": resolution_score,
            "resolution_signal": resolution_signal,
            "resolution_reason": resolution_reason,

            "microstructure_score": micro["microstructure_score"],
            "microstructure_reasons": micro["microstructure_reasons"],

            "quote_state": micro.get("quote_state"),
            "best_bid": micro.get("best_bid"),
            "best_ask": micro.get("best_ask"),
            "mid_price": micro.get("mid_price"),
            "spread": micro.get("spread"),
            "liquidity_usd": micro.get("liquidity_usd"),
            "volume_total_usd": micro.get("volume_total_usd"),

            "reference_price_change": micro.get(
                "reference_price_change"
            ),
            "mid_price_change": micro.get("mid_price_change"),
            "liquidity_change": micro.get("liquidity_change"),
            "volume_change": micro.get("volume_change"),
            "spread_change": micro.get("spread_change"),
            "observation_interval_seconds": micro.get(
                "observation_interval_seconds"
            ),

            "depth_bps": None,
            "quote_age_seconds": None,
        }

        if relation_type == "bucket_member":
            return {
                "decision": "REJECT",
                "reason": (
                    structural_reason
                    or "structural_group_requires_basket_execution"
                ),
                "analysis": analysis,
                "candidate": candidate,
            }

        return {
            "decision": "REJECT",
            "reason": "no_calibrated_directional_alpha_model",
            "analysis": analysis,
            "candidate": candidate,
        }

