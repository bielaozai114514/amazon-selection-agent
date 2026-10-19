import unittest

from tools import forecast, profit


def product():
    return {
        "fob_usd": 4.2,
        "price_usd": 24.99,
        "weight_oz": 9,
        "dims_in": {"length_in": 8, "width_in": 6, "height_in": 1.2},
        "month_sales": 800,
        "monthly_fixed_usd": 500,
        "initial_stock_units": 1600,
    }


class ForecastTest(unittest.TestCase):
    def test_three_scenarios_present(self):
        r = forecast.run(product())
        self.assertEqual(list(r["scenarios"].keys()), ["悲观", "中性", "乐观"])

    def test_optimistic_beats_pessimistic(self):
        r = forecast.run(product())
        self.assertGreater(r["scenarios"]["乐观"]["total_profit"], r["scenarios"]["悲观"]["total_profit"])

    def test_each_scenario_has_twelve_months(self):
        r = forecast.run(product())
        for s in r["scenarios"].values():
            self.assertEqual(len(s["months"]), 12)

    def test_initial_outlay_equals_stock_times_fob(self):
        p = product()
        r = forecast.run(p)
        self.assertAlmostEqual(r["initial_outlay"], 1600 * 4.2, places=2)

    def test_payback_is_none_or_first_positive_month(self):
        r = forecast.run(product())
        for s in r["scenarios"].values():
            if s["payback_month"] is None:
                self.assertLess(s["ending_cash"], 0)
            else:
                row = s["months"][s["payback_month"] - 1]
                self.assertGreaterEqual(row["cumulative"], 0)


if __name__ == "__main__":
    unittest.main()
