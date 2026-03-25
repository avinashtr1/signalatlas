from datetime import datetime, timezone
import uuid

class BasketExecutor:

    def __init__(self, paper_executor, inventory):
        self.paper_executor = paper_executor
        self.inventory = inventory
        self.baskets = {}

    def execute_basket(self, legs):
        """
        legs = list of dicts:
        {
            "decision_result": result,
            "trade_size": size
        }
        """

        basket_id = str(uuid.uuid4())
        opened_positions = []

        for leg in legs:
            result = leg["decision_result"]
            size = leg["trade_size"]

            trade_id = result["candidate"].candidate_id

            locked = self.inventory.lock_capital_for_fill(
                trade_id,
                result["candidate"],
                size
            )

            if not locked:
                continue

            pos = self.paper_executor.execute_trade(result, size)

            self.inventory.finalize_lock_after_fill(trade_id, pos)

            opened_positions.append(pos)

        self.baskets[basket_id] = {
            "basket_id": basket_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "positions": opened_positions,
        }

        return self.baskets[basket_id]
