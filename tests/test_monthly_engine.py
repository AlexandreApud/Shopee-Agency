"""
Unit tests for PackageRepository and MonthlyEngine SQLite components.
"""

import unittest
import pandas as pd
from datetime import timedelta

from database.connection import get_db_connection
from database.repository import PackageRepository
from services.monthly_engine import MonthlyEngine
from config import (
    COL_PACKAGE_TYPE,
    COL_UNIT_REVENUE,
    COL_LEAD_TIME_BUSINESS_FORMATTED,
    PACKAGE_TYPE_RETURN,
    PACKAGE_TYPE_STANDARD,
    PACKAGE_TYPE_COLLECTION,
)


class TestMonthlyEngine(unittest.TestCase):
    """Test suite for SQLite repository upsert and monthly calculation."""

    def setUp(self):
        self.repo = PackageRepository()
        self.engine = MonthlyEngine(self.repo)

    def test_upsert_and_monthly_calculation(self):
        # Synthetic drop-off data for month 1999-01
        df_drop = pd.DataFrame(
            {
                "Tracking": ["TEST_DROP_1", "TEST_DROP_2"],
                "Tag": ["Return/Refund", "-"],
                "Col2": ["", ""],
                "Col3": ["", ""],
                "Col4": ["", ""],
                "Col5": ["", ""],
                "Col6": ["", ""],
                "Col7": ["", ""],
                "Inbound": ["1999-01-15 10:00:00", "1999-01-15 11:00:00"],
                "Outbound": ["1999-01-15 12:00:00", "1999-01-15 13:00:00"],
                "Status": ["DOP_Outbound", "DOP_Outbound"],
                COL_PACKAGE_TYPE: [PACKAGE_TYPE_RETURN, PACKAGE_TYPE_STANDARD],
                COL_UNIT_REVENUE: [0.80, 0.70],
                COL_LEAD_TIME_BUSINESS_FORMATTED: ["02:00:00", "02:00:00"],
                "Lead Time Útil (Minutos)": [120.0, 120.0],
            }
        )

        # Synthetic collection data for month 1999-01
        df_coll = pd.DataFrame(
            {
                "Tracking": ["TEST_COLL_1"],
                "Col1": [""],
                "Col2": [""],
                "Col3": [""],
                "Col4": [""],
                "Col5": [""],
                "Inbound": ["1999-01-15 09:00:00"],
                "Outbound": ["1999-01-15 14:00:00"],
                "Col8": [""],
                "Status": ["Collected"],
                COL_PACKAGE_TYPE: [PACKAGE_TYPE_COLLECTION],
                COL_UNIT_REVENUE: [0.70],
            }
        )

        # Ingest
        d_count = self.repo.upsert_dropoff_dataframe(df_drop, "test_drop.xlsx")
        c_count = self.repo.upsert_collection_dataframe(df_coll, "test_coll.csv")
        self.assertEqual(d_count, 2)
        self.assertEqual(c_count, 1)

        # Query month
        lead_s, rev_s, d_df, c_df = self.engine.compute_month_summary("1999-01")
        self.assertEqual(rev_s.total_packages_moved, 3)
        self.assertEqual(rev_s.return_count, 1)  # 1 return
        self.assertEqual(rev_s.pooled_postagem_count, 2)  # 1 standard drop + 1 collection
        self.assertAlmostEqual(rev_s.return_revenue, 0.80)
        self.assertAlmostEqual(rev_s.pooled_postagem_revenue, 1.40)  # 2 x 0.70 = 1.40
        self.assertAlmostEqual(rev_s.total_revenue, 2.20)
        self.assertEqual(rev_s.dispatched_drop_count, 2)
        self.assertEqual(rev_s.pending_drop_count, 0)
        self.assertEqual(rev_s.collected_count, 1)
        self.assertEqual(rev_s.pending_collection_count, 0)
        self.assertEqual(rev_s.total_dispatched_count, 3)
        self.assertEqual(rev_s.total_pending_count, 0)

        # Lead time
        self.assertIsNotNone(lead_s)
        self.assertEqual(lead_s.dispatched_packages, 2)
        self.assertEqual(lead_s.average_business_time, timedelta(hours=2))

        # Cleanup test records
        conn = get_db_connection()
        conn.execute("DELETE FROM dropoff_orders WHERE tracking_code LIKE 'TEST_%';")
        conn.execute("DELETE FROM collection_orders WHERE tracking_code LIKE 'TEST_%';")
        conn.commit()
        conn.close()


if __name__ == "__main__":
    unittest.main()
