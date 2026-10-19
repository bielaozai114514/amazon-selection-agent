import unittest

from tools import profit


class SizeTierTest(unittest.TestCase):
    def test_sixteen_ounces_stays_small_standard(self):
        d = {"length_in": 10, "width_in": 8, "height_in": 1}
        self.assertEqual(profit.size_class(16, d), "small_standard")

    def test_over_sixteen_ounces_becomes_large_standard(self):
        d = {"length_in": 10, "width_in": 8, "height_in": 1}
        self.assertEqual(profit.size_class(17, d), "large_standard")

    def test_over_twenty_pounds_becomes_bulky(self):
        d = {"length_in": 10, "width_in": 8, "height_in": 6}
        self.assertEqual(profit.size_class(321, d), "large_bulky")


class FeeTest(unittest.TestCase):
    def setUp(self):
        self.table = profit.load(profit.DATA / "fba_fees.json")

    def test_small_standard_fee_by_weight(self):
        self.assertEqual(profit.pickup_fee(9, "small_standard", self.table), 3.43)

    def test_weights_use_kilograms_not_pounds(self):
        product = {
            "fob_usd": 4.0,
            "price_usd": 20.0,
            "weight_oz": 9,
            "dims_in": {"length_in": 8, "width_in": 6, "height_in": 1.2},
            "shipping_per_kg": 8.0,
        }
        r = profit.calc(product)
        self.assertAlmostEqual(r["chargeable_kg"], 0.2551, places=3)
        self.assertAlmostEqual(r["freight"], 2.04, places=2)


class DutyTest(unittest.TestCase):
    def test_hs_override_adds_section_301_on_top_of_mfn(self):
        table = profit.load(profit.DATA / "duty_rates.json")
        self.assertAlmostEqual(profit.duty_for("CN", "9405.40", table), 0.285, places=4)

    def test_unknown_hs_falls_back_to_origin_default(self):
        table = profit.load(profit.DATA / "duty_rates.json")
        self.assertAlmostEqual(profit.duty_for("CN", "0000.00", table), 0.25, places=4)


if __name__ == "__main__":
    unittest.main()
