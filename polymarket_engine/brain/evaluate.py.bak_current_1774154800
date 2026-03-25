from polymarket_engine.market_state_cache import MarketStateCache
from .liquidity_vacuum import LiquidityVacuumDetector
from .microstructure import MicrostructureAnalyzer
from .resolution_arb import ResolutionArbDetector
from ..models.candidate_opportunity import CandidateOpportunity
from ..config.market_filters import MarketFilterConfig
from polymarket_engine.brain.gates import Gates
from polymarket_engine.brain.inventory import Inventory

T_BASE_FILL_PROB = {"HIGH": 0.98, "MEDIUM": 0.90, "LOW": 0.60, "DEFAULT": 0.30}
T_BASE_SLIPPAGE_PCT = {"HIGH": 0.002, "MEDIUM": 0.008, "LOW": 0.015, "DEFAULT": 0.03}
T_FEE_COST_PCT = 0.01

T_MIN_SIGNAL_STRENGTH = 380
T_MIN_STRUCTURAL_EDGE = 0.08
T_MIN_RAW_STRUCTURAL_EDGE = 0.03

T_MIN_BUCKET_SUM = 0.97
T_MAX_BUCKET_SUM = 1.12
T_MIN_BUCKET_COUNT = 2
T_MAX_BUCKET_COUNT = 20
T_MIN_PRICE = 0.01
T_MAX_PRICE = 0.99

# explicit standalone / alternative entry rules
T_MIN_MICRO_VAC_TOTAL_EDGE = 0.20
T_MIN_MICROSTRUCTURE_SCORE = 0.05
T_MIN_VACUUM_SCORE = 0.20

T_MIN_RESOLUTION_TOTAL_EDGE = 0.20
T_MIN_RESOLUTION_SCORE = 0.20


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
        details = candidate.signal_details or {}
        relation_type = details.get("relation_type")
        market_price = candidate.market_state.current_price

        structural_edge = 0.0
        trade_side = "LONG"
        reject_reason = None

        if relation_type == "bucket_member":
            prices = details.get("bucket_group_prices") or []
            bucket_count = len(prices)

            if bucket_count < T_MIN_BUCKET_COUNT or bucket_count > T_MAX_BUCKET_COUNT:
                return 0.0, "LONG", "bucket_count_out_of_range"

            if market_price < T_MIN_PRICE or market_price > T_MAX_PRICE:
                return 0.0, "LONG", "tail_contract_filtered"

            total_yes = sum(float(x) for x in prices)

            if total_yes < T_MIN_BUCKET_SUM or total_yes > T_MAX_BUCKET_SUM:
                return 0.0, "LONG", "bucket_sum_out_of_range"

            if total_yes > 1.0:
                structural_edge = total_yes - 1.0
                trade_side = "SHORT"
            elif total_yes < 1.0:
                structural_edge = 1.0 - total_yes
                trade_side = "LONG"

        return structural_edge, trade_side, reject_reason

    def evaluate_candidate(self, candidate: CandidateOpportunity):
        if candidate.signal_strength is None:
            return {"decision": "REJECT", "reason": "missing_signal", "analysis": {}, "candidate": candidate}

        if candidate.trigger_type != "market_scan" and candidate.signal_strength < T_MIN_SIGNAL_STRENGTH:
            return {"decision": "REJECT", "reason": "weak_signal", "analysis": {}, "candidate": candidate}

        structural_edge, trade_side, structural_reject = self._structural_signal(candidate)

        cache_features = self.market_cache.compute_features(candidate.market_state)
        micro = self.microstructure.analyze(candidate, cache_features)

        vacuum_score, vacuum_signal, vacuum_reason = self.vacuum_detector.detect(candidate, cache_features)
        resolution_score, resolution_signal, resolution_reason = self.resolution_arb.detect(candidate)

        total_edge = structural_edge
        if vacuum_signal:
            total_edge += vacuum_score * 0.05
        if resolution_signal:
            total_edge += resolution_score
        total_edge += micro["microstructure_score"]

        if structural_reject:
            return {
                "decision": "REJECT",
                "reason": structural_reject,
                "analysis": {
                    "structural_edge": structural_edge,
                    "microstructure_score": micro["microstructure_score"],
                },
                "candidate": candidate
            }

        expected_fill_probability = T_BASE_FILL_PROB.get(
            candidate.liquidity_quality,
            T_BASE_FILL_PROB["DEFAULT"]
        )
        expected_slippage = T_BASE_SLIPPAGE_PCT.get(
            candidate.liquidity_quality,
            T_BASE_SLIPPAGE_PCT["DEFAULT"]
        )

        candidate.raw_edge = total_edge
        candidate.expected_net_edge = total_edge * expected_fill_probability - (T_FEE_COST_PCT + expected_slippage)

        rank_score = (
            float(total_edge or 0.0) * float(getattr(self.config, "W_NET_EDGE", 0.5) if hasattr(self.config, "W_NET_EDGE") else 0.5)
            + float(expected_fill_probability or 0.0) * 0.2
            + float(max(0.0, structural_edge) or 0.0) * 0.3
        )

        candidate.signal_details = dict(candidate.signal_details or {})
        candidate.signal_details["trade_side"] = trade_side

        analysis = {
            "trade_side": trade_side,
            "structural_edge": structural_edge,
            "total_edge": total_edge,
            "raw_edge": candidate.raw_edge,
            "expected_fill_probability": expected_fill_probability,
            "expected_net_edge_pct": candidate.expected_net_edge * 100.0,
            "annualized_edge_pct": candidate.expected_net_edge * 100.0,
            "vacuum_score": vacuum_score,
            "vacuum_signal": vacuum_signal,
            "vacuum_reason": vacuum_reason,
            "resolution_score": resolution_score,
            "resolution_signal": resolution_signal,
            "resolution_reason": resolution_reason,
            "microstructure_score": micro["microstructure_score"],
            "microstructure_reasons": micro["microstructure_reasons"],
            "price_velocity": micro["price_velocity"],
            "liquidity_change": micro["liquidity_change"],
            "staleness_seconds": micro["staleness_seconds"],
            "volume_usd": micro["volume_usd"],
            "depth_bps": micro["depth_bps"],
            "rank_score": rank_score,
        }

        if candidate.expected_net_edge <= 0:
            return {"decision": "REJECT", "reason": "negative_edge", "analysis": analysis, "candidate": candidate}

        relation_type = (candidate.signal_details or {}).get("relation_type")
        entry_type = None

        # block standalone extreme-tail contracts from filling the book
        market_price = float(getattr(candidate.market_state, "current_price", 0.0) or 0.0)
        is_tail_price = (market_price <= 0.02 or market_price >= 0.98)
        if relation_type != "bucket_member" and is_tail_price:
            return {"decision": "REJECT", "reason": "standalone_tail_blocked", "analysis": analysis, "candidate": candidate}

        # 1) STRUCTURAL
        if relation_type == "bucket_member":
            if structural_edge < T_MIN_RAW_STRUCTURAL_EDGE:
                return {"decision": "REJECT", "reason": "no_structural_edge", "analysis": analysis, "candidate": candidate}
            if total_edge < T_MIN_STRUCTURAL_EDGE:
                return {"decision": "REJECT", "reason": "no_real_edge", "analysis": analysis, "candidate": candidate}
            entry_type = "STRUCTURAL"

        # 2) MICRO + VACUUM
        elif vacuum_signal and vacuum_score >= T_MIN_VACUUM_SCORE and micro["microstructure_score"] >= T_MIN_MICROSTRUCTURE_SCORE:
            if total_edge < T_MIN_MICRO_VAC_TOTAL_EDGE:
                return {"decision": "REJECT", "reason": "micro_vacuum_too_weak", "analysis": analysis, "candidate": candidate}
            entry_type = "MICRO_VACUUM"

        # 3) RESOLUTION
        elif resolution_signal and resolution_score >= T_MIN_RESOLUTION_SCORE:
            if total_edge < T_MIN_RESOLUTION_TOTAL_EDGE:
                return {"decision": "REJECT", "reason": "resolution_too_weak", "analysis": analysis, "candidate": candidate}
            entry_type = "RESOLUTION"

        else:
            return {"decision": "REJECT", "reason": "no_valid_entry_type", "analysis": analysis, "candidate": candidate}

        analysis["entry_type"] = entry_type

        # execution branch split
        if (
            entry_type in {"MICRO_VACUUM", "STRUCTURAL"}
            and float(micro.get("microstructure_score", 0.0) or 0.0) >= 0.20
            and float(vacuum_score or 0.0) >= 0.20
            and float(expected_fill_probability or 0.0) >= 0.90
        ):
            execution_mode = "ACTIVE"
        else:
            execution_mode = "PASSIVE"

        analysis["execution_mode"] = execution_mode

        # HARD MICROSTRUCTURE FILTER (block dead / stale markets)
        micro = float(analysis.get("microstructure_score", 0.0) or 0.0)
        reasons = analysis.get("microstructure_reasons", []) or []
        if micro <= 0.10 or "stale_price" in reasons:
            return {"decision": "REJECT", "reason": "BAD_MICROSTRUCTURE", "analysis": analysis, "candidate": candidate}

        passes_gates, gate_reason = self.gates.check(candidate)
        if not passes_gates:
            return {"decision": "REJECT", "reason": gate_reason, "analysis": analysis, "candidate": candidate}

        passes_inventory, inv_reason = self.inventory.check(candidate)
        if not passes_inventory:
            return {"decision": "REJECT", "reason": inv_reason, "analysis": analysis, "candidate": candidate}

        return {"decision": "ACCEPT", "reason": entry_type, "analysis": analysis, "candidate": candidate}
