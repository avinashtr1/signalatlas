from datetime import datetime, timezone
import collections

class Inventory:
    def check(self, candidate):
        return True, None

    def __init__(self, total_capital=100000.0):
        self._total_capital = total_capital
        self._locked_capital = {}
        self.realized_pnl = 0.0
        self.exposure_by_strategy = collections.defaultdict(float)

    @property
    def locked_capital_total(self):
        return sum(self._locked_capital.values())

    @property
    def free_capital(self):
        return self._total_capital + self.realized_pnl - self.locked_capital_total

    def can_lock_capital(self, amount: float):
        return self.free_capital >= amount

    def lock_capital_for_fill(self, trade_id, candidate, intended_size):
        details = candidate.signal_details or {}
        side = details.get("trade_side", "LONG")
        px = candidate.market_state.current_price

        if side == "SHORT":
            amount = intended_size * (1.0 - px)
        else:
            amount = intended_size * px

        if not self.can_lock_capital(amount):
            return False

        self._locked_capital[trade_id] = amount
        return True

    def finalize_lock_after_fill(self, trade_id, opened_position):
        if trade_id not in self._locked_capital:
            return

        if not opened_position:
            del self._locked_capital[trade_id]
        else:
            self._locked_capital[trade_id] = opened_position["allocated_capital"]
            self.exposure_by_strategy[opened_position["strategy_type"]] += opened_position["allocated_capital"]

    def release_and_realize_pnl(self, trade_id, pnl, strategy):
        if trade_id not in self._locked_capital:
            return
        locked_amount = self._locked_capital.pop(trade_id)
        self.exposure_by_strategy[strategy] -= locked_amount
        self.realized_pnl += pnl

    def get_summary(self, paper_executor):
        exec_summary = paper_executor.get_summary()
        return {
            "capital_state": {"free_capital": self.free_capital, "locked_capital": self.locked_capital_total},
            "pnl_state": {"realized_pnl": self.realized_pnl, "unrealized_pnl": exec_summary["total_unrealized_pnl"]},
            "position_state": {"open_positions_count": exec_summary["open_positions_count"], "closed_positions_count": exec_summary["closed_positions_count"]},
            "exposure_by_strategy": dict(self.exposure_by_strategy)
        }
