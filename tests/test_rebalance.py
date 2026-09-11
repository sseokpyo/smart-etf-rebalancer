from decimal import Decimal
import unittest

from invest_bot.strategy import rebalance_with_new_cash


TARGETS = {"QQQ": Decimal(".40"), "TQQQ": Decimal(".20"), "SPY": Decimal(".20"), "SCHD": Decimal(".20")}


class RebalanceTests(unittest.TestCase):
    def test_new_cash_is_used_before_any_sale(self):
        plan = rebalance_with_new_cash(
            {"QQQ": Decimal("40"), "TQQQ": Decimal("0"), "SPY": Decimal("20"), "SCHD": Decimal("20")},
            TARGETS, Decimal("20"), Decimal("1"), Decimal(".05"),
        )
        self.assertFalse(plan.sell_rebalance_required)
        self.assertEqual(plan.buys["TQQQ"], Decimal("20.00"))
        self.assertTrue(all(value == 0 for value in plan.sells.values()))

    def test_sell_rebalance_only_happens_when_drift_remains_large(self):
        plan = rebalance_with_new_cash(
            {"QQQ": Decimal("40"), "TQQQ": Decimal("40"), "SPY": Decimal("10"), "SCHD": Decimal("10")},
            TARGETS, Decimal("10"), Decimal("1"), Decimal(".05"),
        )
        self.assertTrue(plan.sell_rebalance_required)
        self.assertEqual(plan.sells["TQQQ"], Decimal("18.00"))
        self.assertEqual(plan.buys["SPY"], Decimal("12.00"))
        self.assertEqual(plan.buys["SCHD"], Decimal("12.00"))


if __name__ == '__main__':
    unittest.main()
