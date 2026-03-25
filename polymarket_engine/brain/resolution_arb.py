from datetime import datetime, timezone


class ResolutionArbDetector:
    """
    Boosts candidates when:
    - time to resolution is relatively short
    - price is extreme / asymmetric
    - objective resolution support exists

    Returns: (score, signal, reason)
    """

    def detect(self, candidate):
        ms = candidate.market_state
        now = datetime.now(timezone.utc)

        end_time = ms.end_time
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        hours_to_resolution = max(0.0, (end_time - now).total_seconds() / 3600.0)
        px = float(ms.current_price)
        objective = bool(getattr(ms, "objective_support", False))

        score = 0.0
        reason = None

        # very near resolution + extreme pricing
        if objective and hours_to_resolution <= 72:
            if px <= 0.10 or px >= 0.90:
                score = 0.20
                reason = "near_resolution_extreme_price"
            elif px <= 0.20 or px >= 0.80:
                score = 0.10
                reason = "near_resolution_skewed_price"

        # medium horizon, still worth something
        elif objective and hours_to_resolution <= 168:
            if px <= 0.08 or px >= 0.92:
                score = 0.10
                reason = "weekly_resolution_extreme_price"

        return score, bool(score > 0.0), reason
