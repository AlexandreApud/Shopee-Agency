"""
Unit tests for RevenueCalculator service with pooled postagem and collection.
"""

import unittest
import pandas as pd

from config import (
    COL_PACKAGE_TYPE,
    COL_UNIT_REVENUE,
    COL_CUMULATIVE_REVENUE,
    PACKAGE_TYPE_RETURN,
    PACKAGE_TYPE_STANDARD,
    PACKAGE_TYPE_COLLECTION,
)
from services.revenue_calculator import RevenueCalculator


class TestRevenueCalculator(unittest.TestCase):
    """Test suite for RevenueCalculator functionality."""

    def setUp(self):
        self.calculator = RevenueCalculator()

    def test_return_detection(self):
        self.assertTrue(self.calculator.is_return_package("Return/Refund"))
        self.assertTrue(self.calculator.is_return_package("returned"))
        self.assertTrue(self.calculator.is_return_package("REFUND"))
        self.assertTrue(self.calculator.is_return_package("Devolução"))
        self.assertFalse(self.calculator.is_return_package("-"))
        self.assertFalse(self.calculator.is_return_package(None))

    def test_standard_tier_rates(self):
        self.assertEqual(self.calculator.get_standard_tier_rate(1), 0.70)
        self.assertEqual(self.calculator.get_standard_tier_rate(500), 0.70)
        self.assertEqual(self.calculator.get_standard_tier_rate(501), 0.60)
        self.assertEqual(self.calculator.get_standard_tier_rate(1000), 0.60)
        self.assertEqual(self.calculator.get_standard_tier_rate(1001), 0.50)
        self.assertEqual(self.calculator.get_standard_tier_rate(1500), 0.50)
        self.assertEqual(self.calculator.get_standard_tier_rate(1501), 0.50)

    def test_process_consolidated_revenue(self):
        # 2 returns (2 x 0.80 = 1.60), 2 dropoff standard, 2 collection => 4 pooled at 0.70 = 2.80
        # Total = 1.60 + 2.80 = 4.40
        df_drop = pd.DataFrame({"Tag": ["Return/Refund", "-", "returned", "-"]})
        df_coll = pd.DataFrame({"Order": ["A", "B"]})

        enr_drop, enr_coll, summary = self.calculator.process_consolidated_revenue(
            df_dropoff=df_drop, tag_col="Tag", df_collection=df_coll
        )

        self.assertEqual(summary.total_packages_moved, 6)
        self.assertEqual(summary.return_count, 2)
        self.assertEqual(summary.standard_drop_count, 2)
        self.assertEqual(summary.collection_count, 2)
        self.assertEqual(summary.pooled_postagem_count, 4)
        self.assertAlmostEqual(summary.return_revenue, 1.60)
        self.assertAlmostEqual(summary.pooled_postagem_revenue, 2.80)
        self.assertAlmostEqual(summary.total_revenue, 4.40)
        self.assertAlmostEqual(summary.average_ticket, 0.73)

        # Drop-off checks
        self.assertEqual(enr_drop.loc[0, COL_PACKAGE_TYPE], PACKAGE_TYPE_RETURN)
        self.assertEqual(enr_drop.loc[0, COL_UNIT_REVENUE], 0.80)
        self.assertEqual(enr_drop.loc[1, COL_PACKAGE_TYPE], PACKAGE_TYPE_STANDARD)
        self.assertEqual(enr_drop.loc[1, COL_UNIT_REVENUE], 0.70)

        # Collection checks
        self.assertEqual(enr_coll.loc[0, COL_PACKAGE_TYPE], PACKAGE_TYPE_COLLECTION)
        self.assertEqual(enr_coll.loc[0, COL_UNIT_REVENUE], 0.70)


if __name__ == "__main__":
    unittest.main()
