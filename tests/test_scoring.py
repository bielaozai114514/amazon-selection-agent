import unittest

from tools import compliance, profit, scoring


def base_product():
    return {
        "title": "普通收纳盒",
        "category": "tools",
        "fob_usd": 4.0,
        "price_usd": 25.0,
        "weight_oz": 10,
        "dims_in": {"length_in": 8, "width_in": 6, "height_in": 2},
        "month_sales": 600,
        "avg_reviews_top3": 900,
        "brand_concentration": 0.3,
    }


class HardFilterTest(unittest.TestCase):
    def test_low_margin_rejects(self):
        p = base_product()
        p["fob_usd"] = 15.0
        pr = profit.calc(p)
        c = compliance.check(p)
        self.assertEqual(scoring.score(p, pr, c)["verdict"], "reject")

    def test_brand_hit_rejects_through_compliance_level(self):
        p = base_product()
        p["title"] = "Disney 米奇收纳盒"
        pr = profit.calc(p)
        c = compliance.check(p)
        self.assertEqual(c["level"], "high")
        self.assertEqual(scoring.score(p, pr, c)["verdict"], "reject")

    def test_healthy_product_passes(self):
        p = base_product()
        pr = profit.calc(p)
        c = compliance.check(p)
        self.assertEqual(scoring.score(p, pr, c)["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
