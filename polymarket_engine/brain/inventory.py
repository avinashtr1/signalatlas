from collections import defaultdict

class Inventory:
    def __init__(self, paper_balance=100000.0):
        self.paper_balance = float(paper_balance)
        self._total_capital = float(paper_balance)

        self.max_open_trades = 42
        self.max_exposure_usdc = 6000.0
        self.max_trade_usdc = 1000.0

        self.open_trades_count = 0
        self.total_exposure_usdc = 0.0

        self._locked_capital = {}
        self.exposure_by_strategy = defaultdict(float)
        self.realized_pnl = 0.0

    @property
    def locked_capital_total(self):
        return float(sum(self._locked_capital.values()))

    @property
    def free_capital(self):
        return float(self._total_capital + self.realized_pnl - self.locked_capital_total)

    def check(self, candidate):
        if self.open_trades_count >= self.max_open_trades:
            return False, "MAX_OPEN_TRADES_REACHED"
        return True, "INVENTORY_OK"

    def can_lock_capital(self, amount):
        amount = float(amount or 0.0)
        if amount > self.max_trade_usdc:
            return False
        if (self.locked_capital_total + amount) > self.max_exposure_usdc:
            return False
        if amount > self.free_capital:
            return False
        return True

    def lock_capital_for_fill(self, trade_id, candidate, amount):
        amount = float(amount or 0.0)
        if not self.can_lock_capital(amount):
            return False
        self._locked_capital[str(trade_id)] = amount
        return True

    def finalize_lock_after_fill(self, trade_id, opened_position):
        trade_id = str(trade_id)
        alloc = float((opened_position or {}).get("allocated_capital", 0.0) or 0.0)
        self._locked_capital[trade_id] = alloc
        strategy = (opened_position or {}).get("strategy_type", "TEST_STRATEGY")
        self.exposure_by_strategy[strategy] += alloc
        self.open_trades_count += 1
        self.total_exposure_usdc = self.locked_capital_total

    def release_capital_for_close(self, trade_id, closed_position=None):
        trade_id = str(trade_id)
        alloc = float(self._locked_capital.pop(trade_id, 0.0) or 0.0)
        strategy = (closed_position or {}).get("strategy_type", "TEST_STRATEGY") if closed_position else "TEST_STRATEGY"
        self.exposure_by_strategy[strategy] = max(0.0, float(self.exposure_by_strategy.get(strategy, 0.0)) - alloc)
        self.open_trades_count = max(0, self.open_trades_count - 1)
        self.total_exposure_usdc = self.locked_capital_total

    def get_summary(self, paper_executor=None):
        open_positions_count = 0
        closed_positions_count = 0
        unrealized_pnl = 0.0

        if paper_executor is not None:
            open_positions = paper_executor.get_open_positions()
            open_positions_count = len(open_positions)
            closed_positions_count = len([p for p in paper_executor.positions.values() if p.get("status") == "CLOSED"])
            unrealized_pnl = float(sum(float(p.get("unrealized_pnl", 0.0) or 0.0) for p in open_positions))

            self.open_trades_count = open_positions_count
            self.total_exposure_usdc = self.locked_capital_total

        return {
            "capital_state": {
                "free_capital": self.free_capital,
                "locked_capital": self.locked_capital_total,
            },
            "pnl_state": {
                "realized_pnl": float(self.realized_pnl),
                "unrealized_pnl": unrealized_pnl,
            },
            "position_state": {
                "open_positions_count": open_positions_count,
                "closed_positions_count": closed_positions_count,
            },
            "exposure_by_strategy": dict(self.exposure_by_strategy),
        }


    def release_and_realize_pnl(self, trade_id, realized_pnl, strategy_type="TEST_STRATEGY"):
        trade_id = str(trade_id)
        alloc = float(self._locked_capital.pop(trade_id, 0.0) or 0.0)
        self.realized_pnl += float(realized_pnl or 0.0)
        self.exposure_by_strategy[str(strategy_type)] = max(
            0.0,
            float(self.exposure_by_strategy.get(str(strategy_type), 0.0)) - alloc
        )
        self.open_trades_count = max(0, self.open_trades_count - 1)
        self.total_exposure_usdc = self.locked_capital_total

