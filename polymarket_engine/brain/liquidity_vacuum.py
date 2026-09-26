class LiquidityVacuumDetector:
    """
    Disabled pending calibration against genuine CLOB depth.

    Reported aggregate liquidity changes alone are not sufficient evidence
    of an executable liquidity vacuum.
    """

    def detect(self, candidate, cache_features=None):
        return (
            0.0,
            False,
            "vacuum_model_disabled_pending_real_depth",
        )
