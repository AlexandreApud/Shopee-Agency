"""
Unit tests for LeadTimeCalculator component with business hours.
"""

import unittest
from datetime import timedelta
import pandas as pd

from config import COL_PROCESSING_STATUS, STATUS_COMPLETED, STATUS_PENDING
from services.lead_time_calculator import LeadTimeCalculator


class TestLeadTimeCalculator(unittest.TestCase):
    """Test suite for LeadTimeCalculator functionality with business hours."""

    def setUp(self):
        self.calculator = LeadTimeCalculator()

    def test_format_timedelta_standard(self):
        td = timedelta(hours=1, minutes=5, seconds=30)
        formatted = self.calculator.format_timedelta(td)
        self.assertEqual(formatted, "01:05:30")

    def test_format_timedelta_with_days(self):
        td = timedelta(days=2, hours=3, minutes=10, seconds=5)
        formatted = self.calculator.format_timedelta(td)
        self.assertEqual(formatted, "2d 03:10:05")

    def test_format_timedelta_none(self):
        formatted = self.calculator.format_timedelta(None)
        self.assertEqual(formatted, "N/A")

    def test_process_lead_times_with_mixed_records(self):
        # 2026-09-02 is Wednesday (open 08:00 to 19:30)
        data = {
            "Inbound Time": [
                "2026-09-02 10:00:00",
                "2026-09-02 11:00:00",
                "2026-09-02 12:00:00",
            ],
            "Outbound Time": [
                "2026-09-02 11:30:00",  # 90 min
                "2026-09-02 11:45:00",  # 45 min
                None,                   # Pending
            ],
        }
        df = pd.DataFrame(data)

        enriched_df, summary = self.calculator.process_lead_times(
            df, inbound_col="Inbound Time", outbound_col="Outbound Time"
        )

        self.assertEqual(summary.total_packages, 3)
        self.assertEqual(summary.dispatched_packages, 2)
        self.assertEqual(summary.pending_packages, 1)

        # Expected average: (90 + 45) / 2 = 67.5 minutes = 1h 07m 30s
        self.assertAlmostEqual(summary.average_business_minutes, 67.5)
        self.assertEqual(summary.average_business_time, timedelta(minutes=67, seconds=30))

        # Check row status
        self.assertEqual(enriched_df.loc[0, COL_PROCESSING_STATUS], STATUS_COMPLETED)
        self.assertEqual(enriched_df.loc[1, COL_PROCESSING_STATUS], STATUS_COMPLETED)
        self.assertEqual(enriched_df.loc[2, COL_PROCESSING_STATUS], STATUS_PENDING)


if __name__ == "__main__":
    unittest.main()
