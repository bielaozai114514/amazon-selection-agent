"""类目校验测试：认证清单错整张就错，必须锁住。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import compliance


class CategoryValidationTest(unittest.TestCase):
    def test_unknown_category_warns(self):
        """category 不在认证映射表里时必须告警，不能静默返回空清单。"""
        product = {"title": "某产品", "category": "nonexistent_category"}
        warnings = compliance.validate_category(product)
        self.assertTrue(
            any("不在认证映射表" in w for w in warnings),
            f"未检测到未知类目告警，实际：{warnings}",
        )

    def test_food_contact_mismatch_warns(self):
        """水杯填成 tools，必须提示疑似食品接触类目。"""
        product = {"title": "硅胶折叠水杯 750ml", "category": "tools"}
        warnings = compliance.validate_category(product)
        self.assertTrue(
            any("food_contact" in w for w in warnings),
            f"未检测到类目冲突告警，实际：{warnings}",
        )

    def test_correct_category_no_warning(self):
        """类目填对时不该有噪音告警。"""
        product = {"title": "硅胶折叠水杯 750ml", "category": "food_contact"}
        self.assertEqual(compliance.validate_category(product), [])

    def test_makeup_mirror_not_flagged_as_beauty(self):
        """化妆镜含 makeup，但它是镜子不是化妆品，不能误报。"""
        product = {
            "title": "便携 LED 化妆镜 可折叠 带补光",
            "keyword": "portable led makeup mirror",
            "category": "electronics",
        }
        self.assertEqual(compliance.validate_category(product), [])

    def test_check_embeds_warnings(self):
        """check() 要把告警一并返回，供报告渲染。"""
        result = compliance.check({"title": "硅胶折叠水杯", "category": "tools"})
        self.assertIn("category_warnings", result)
        self.assertTrue(result["category_warnings"])


if __name__ == "__main__":
    unittest.main()
